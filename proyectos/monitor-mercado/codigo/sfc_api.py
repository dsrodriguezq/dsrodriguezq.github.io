"""
Cliente de los datos abiertos de tasas y desembolsos de la Superintendencia Financiera
de Colombia, publicados en datos.gov.co (plataforma Socrata).

Dos conjuntos de datos con el mismo esquema:
    RECIENTE   qzsc-9esp   solo los últimos ~2 meses; rápido, se pide un mes completo de una vez
    HISTORICO  w9zh-vetq   todo el histórico; pesado, se pide por tramos de días

Decisiones de diseño:
  - Sin $order ni $group en las consultas: en estos conjuntos vuelven las consultas lentas.
    Solo $where sobre fecha_corte, $limit y $offset.
  - Como $offset sin orden no es estable, se descartan filas repetidas entre páginas.
  - Los errores pasajeros del servidor (429, 500, 502, 503, 504) y los tiempos de espera
    se reintentan; si persisten, se levanta ErrorFuente para que quien llama decida
    (por ejemplo, partir el tramo en dos).
  - Solo se conservan establecimientos bancarios.
"""
import os
import time

import pandas as pd
import requests

BASE = "https://www.datos.gov.co/resource"
RECIENTE = "qzsc-9esp"
HISTORICO = "w9zh-vetq"
TIPO_ENTIDAD = "BC-ESTABLECIMIENTO BANCARIO"

DIMENSIONES = ["nombre_entidad", "codigo_municipio", "tipo_de_cr_dito", "producto_de_cr_dito", "plazo_de_cr_dito"]
CAMPOS = ["nombre_tipo_entidad", "fecha_corte"] + DIMENSIONES + [
    "tasa_efectiva_promedio", "montos_desembolsados", "numero_de_creditos"]
METRICAS = ["monto", "creditos", "desembolsos", "monto_con_tasa", "tasa_x_monto"]

TAMANO_PAGINA = 50_000
ESPERA_SEGUNDOS = 120
INTENTOS = 4
TRANSITORIOS = {429, 500, 502, 503, 504}

_sesion = requests.Session()


class ErrorFuente(Exception):
    """La fuente no respondió después de todos los reintentos."""


def _cabeceras():
    token = os.environ.get("SOCRATA_APP_TOKEN")      # opcional: sube el límite de peticiones
    return {"X-App-Token": token} if token else {}


def pedir(conjunto, parametros):
    url = f"{BASE}/{conjunto}.json"
    for intento in range(1, INTENTOS + 1):
        try:
            r = _sesion.get(url, params=parametros, headers=_cabeceras(), timeout=ESPERA_SEGUNDOS)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if intento == INTENTOS:
                raise ErrorFuente(f"sin respuesta tras {INTENTOS} intentos: {type(e).__name__}")
            time.sleep(2 ** intento)
            continue
        if r.status_code in TRANSITORIOS:
            if intento == INTENTOS:
                raise ErrorFuente(f"HTTP {r.status_code} tras {INTENTOS} intentos")
            time.sleep(2 ** intento)
            continue
        r.raise_for_status()
        return r.json()


def cobertura(conjunto=RECIENTE):
    """Primera y última fecha de corte publicadas para bancos."""
    d = pedir(conjunto, {"$select": "min(fecha_corte) AS ini, max(fecha_corte) AS fin",
                         "$where": f"nombre_tipo_entidad='{TIPO_ENTIDAD}'"})[0]
    return pd.Timestamp(d["ini"]), pd.Timestamp(d["fin"])


def descargar(conjunto, inicio, fin):
    """
    Descarga [inicio, fin) fila por fila y devuelve un agregado por periodo + DIMENSIONES.
    Cada fila de la fuente es un registro de desembolso con su monto, tasa y número de créditos.
    """
    where = f"fecha_corte >= '{inicio:%Y-%m-%d}T00:00:00' AND fecha_corte < '{fin:%Y-%m-%d}T00:00:00'"
    vistos, partes, offset, leidas, repetidas = set(), [], 0, 0, 0
    while True:
        pagina = pedir(conjunto, {"$select": ",".join(CAMPOS), "$where": where,
                                  "$limit": TAMANO_PAGINA, "$offset": offset})
        if not pagina:
            break
        df = pd.DataFrame(pagina).reindex(columns=CAMPOS)
        leidas += len(df)
        claves = list(df.astype(str).itertuples(index=False, name=None))
        nuevas = [c not in vistos for c in claves]
        repetidas += len(claves) - sum(nuevas)
        vistos.update(c for c, n in zip(claves, nuevas) if n)
        df = df[nuevas]
        df = df[df.nombre_tipo_entidad == TIPO_ENTIDAD]
        if len(df):
            partes.append(_agregar(df))
        print(f"      {leidas:,} filas leídas", end="\r", flush=True)
        if len(pagina) < TAMANO_PAGINA:
            break
        offset += TAMANO_PAGINA
        time.sleep(0.2)          # cortesía con el servidor entre páginas
    print()
    if repetidas:
        print(f"      {repetidas:,} filas repetidas entre páginas descartadas")
    if not partes:
        return pd.DataFrame(columns=["periodo"] + DIMENSIONES + METRICAS)
    return pd.concat(partes).groupby(["periodo"] + DIMENSIONES, as_index=False)[METRICAS].sum()


def _agregar(df):
    for c in ["tasa_efectiva_promedio", "montos_desembolsados", "numero_de_creditos"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0.0)
    vacios = (df.montos_desembolsados == 0).mean()
    if vacios > 0.3:
        print(f"      [!] {vacios:.0%} de las filas llegaron sin monto: revisar si cambió el esquema de la fuente")
    df = df.rename(columns={"montos_desembolsados": "monto", "numero_de_creditos": "creditos"})
    con_tasa = df.tasa_efectiva_promedio > 0
    df["monto_con_tasa"] = df.monto.where(con_tasa, 0.0)
    df["tasa_x_monto"] = (df.tasa_efectiva_promedio * df.monto).where(con_tasa, 0.0)
    df["desembolsos"] = 1
    df["periodo"] = pd.to_datetime(df.fecha_corte, errors="coerce").dt.strftime("%Y-%m")
    for c in DIMENSIONES:
        df[c] = df[c].fillna("Sin información").astype(str).str.strip()
    df["codigo_municipio"] = df.codigo_municipio.str.extract(r"(\d+)")[0].fillna("0").str.zfill(5)
    return df.groupby(["periodo"] + DIMENSIONES, as_index=False)[METRICAS].sum()
