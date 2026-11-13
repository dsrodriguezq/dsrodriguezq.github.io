"""
Paso 2 · Une todos los meses guardados y construye datos/mercado.json para el tablero.

Transformaciones:
  - Plazo: el texto publicado ("De 1 a 3 años", "Más de 180 días", ...) se lleva a meses y se
    agrupa en rangos. Lo que no tiene plazo (rotativos, tarjeta) queda como "Sin plazo".
  - Banco: nombre corto y legible ("BANCO DE OCCIDENTE S.A." → "Banco de Occidente").
  - Departamento: los dos primeros dígitos del código DIVIPOLA del municipio.
  - Tasa ponderada = Σ(tasa × monto) / Σ(monto con tasa).

Para que el archivo sea liviano, los montos se guardan en millones de pesos y los nombres se
reemplazan por índices de catálogos (dim).
"""
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
MENSUAL = RAIZ / "datos" / "mensual"
SALIDA = RAIZ / "datos" / "mercado.json"
MESES_MAPA = 3   # meses con detalle por departamento

DEPARTAMENTOS = {
    "05": "Antioquia", "08": "Atlántico", "11": "Bogotá D.C.", "13": "Bolívar", "15": "Boyacá", "17": "Caldas",
    "18": "Caquetá", "19": "Cauca", "20": "Cesar", "23": "Córdoba", "25": "Cundinamarca", "27": "Chocó",
    "41": "Huila", "44": "La Guajira", "47": "Magdalena", "50": "Meta", "52": "Nariño", "54": "Norte de Santander",
    "63": "Quindío", "66": "Risaralda", "68": "Santander", "70": "Sucre", "73": "Tolima", "76": "Valle del Cauca",
    "81": "Arauca", "85": "Casanare", "86": "Putumayo", "88": "San Andrés", "91": "Amazonas", "94": "Guainía",
    "95": "Guaviare", "97": "Vaupés", "99": "Vichada",
}
RANGOS = [(12, "Hasta 12 meses"), (36, "13 a 36 meses"), (60, "37 a 60 meses"), (120, "61 a 120 meses"),
          (10 ** 6, "Más de 120 meses")]
ORDEN_PLAZOS = [r[1] for r in RANGOS] + ["Sin plazo"]
UNIDADES = re.compile(r"(\d+(?:[.,]\d+)?)\s*(d[ií]a|mes|a[ñn]o)", re.I)
PARTICULAS = {"de", "del", "la", "las", "los", "y", "e"}


def sin_tildes(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def plazo_en_meses(texto):
    t = sin_tildes(str(texto)).lower()
    valores = []
    for numero, unidad in UNIDADES.findall(t):
        n = float(numero.replace(",", "."))
        valores.append(n / 30 if unidad.startswith("d") else n * 12 if unidad.startswith("a") else n)
    if not valores:
        return None
    meses = max(valores)
    if ("mas de" in t or "mayor" in t) and "hasta" not in t:
        meses += 1                                    # "más de 5 años" cae en el rango siguiente
    return meses


def rango_plazo(texto):
    m = plazo_en_meses(texto)
    if m is None:
        return "Sin plazo"
    return next(etq for tope, etq in RANGOS if m <= tope)


def nombre_banco(n):
    t = re.sub(r"\b(S\.?\s?A\.?\s?S?\.?|SOCIEDAD ANONIMA|COMPAÑ[IÍ]A DE FINANCIAMIENTO)\b", "", str(n), flags=re.I)
    t = re.sub(r"[\s,.]+$", "", re.sub(r"\s+", " ", t)).strip()
    siglas = {"BBVA", "GNB", "AV", "CF", "S.A", "W", "JP"}
    palabras = []
    for i, p in enumerate(t.split(" ")):
        if p.upper() in siglas or (len(p) <= 4 and p.isupper() and not p.isalpha()):
            palabras.append(p.upper())
        elif i > 0 and p.lower() in PARTICULAS:
            palabras.append(p.lower())
        else:
            palabras.append(p.capitalize())
    return " ".join(palabras) or str(n)


def tipo_oracion(t):
    t = str(t).strip()
    return t[:1].upper() + t[1:].lower() if t.isupper() else t


def cargar():
    archivos = sorted(MENSUAL.glob("*.csv.gz"))
    if not archivos:
        raise SystemExit("No hay meses descargados en datos/mensual. Corre primero actualizar.py.")
    partes = []
    for a in archivos:
        df = pd.read_csv(a, dtype={"codigo_municipio": str})
        df["periodo"] = a.name[:7]
        partes.append(df)
    df = pd.concat(partes, ignore_index=True)
    df["banco"] = df.nombre_entidad.map(nombre_banco)
    df["tipo"] = df.tipo_de_cr_dito.map(tipo_oracion)
    df["producto"] = df.producto_de_cr_dito.map(tipo_oracion)
    df["plazo"] = df.plazo_de_cr_dito.map(rango_plazo)
    df["depto"] = df.codigo_municipio.str.zfill(5).str[:2]
    sin_depto = ~df.depto.isin(DEPARTAMENTOS)
    if sin_depto.any():
        print(f"[!] {int(sin_depto.sum())} filas con municipio sin departamento reconocible: quedan como 'Sin información'")
    df.loc[sin_depto, "depto"] = "00"
    return df


def indices(serie, orden=None):
    valores = orden if orden else sorted(serie.unique())
    valores = [v for v in valores if v in set(serie)] + sorted(set(serie) - set(valores))
    return valores, {v: i for i, v in enumerate(valores)}


def exportar_looker(df, g, m):
    """CSV planos para Google Sheets (=IMPORTDATA) y Looker Studio. Montos en millones de pesos.
    Tasa ponderada en Looker: SUM(tasa_x_monto) / SUM(monto_con_tasa)."""
    carpeta = RAIZ / "datos" / "looker"
    carpeta.mkdir(exist_ok=True)
    nombres = {"monto": "monto_millones", "monto_con_tasa": "monto_con_tasa_millones", "tasa_x_monto": "tasa_x_monto"}
    a = g.copy()
    a.insert(0, "fecha", a.periodo + "-01")
    a = a.drop(columns="periodo")
    for c in ("monto", "monto_con_tasa", "tasa_x_monto"):
        a[c] = (a[c] / 1e6).round(4 if c == "tasa_x_monto" else 2)
    a.rename(columns=nombres).to_csv(carpeta / "credito_mensual.csv", index=False)

    d = df.groupby(["periodo", "banco", "depto", "tipo"], as_index=False)[m].sum()
    d.insert(0, "fecha", d.periodo + "-01")
    d["departamento"] = d.depto.map(lambda x: DEPARTAMENTOS.get(x, "Sin información"))
    d["pais"] = "Colombia"
    d = d[["fecha", "banco", "departamento", "pais", "tipo"] + m]
    for c in ("monto", "monto_con_tasa", "tasa_x_monto"):
        d[c] = (d[c] / 1e6).round(4 if c == "tasa_x_monto" else 2)
    d.rename(columns=nombres).to_csv(carpeta / "credito_departamento.csv", index=False)
    print(f"[OK] looker/: {len(a):,} filas mensuales y {len(d):,} por departamento")


def main():
    df = cargar()
    estado = json.loads((MENSUAL / "estado.json").read_text(encoding="utf-8")) if (MENSUAL / "estado.json").exists() else {}
    dims, ix = {}, {}
    for clave, col, orden in (("periodos", "periodo", None), ("bancos", "banco", None), ("tipos", "tipo", None),
                              ("productos", "producto", None), ("plazos", "plazo", ORDEN_PLAZOS)):
        dims[clave], ix[clave] = indices(df[col], orden)

    m = ["monto", "desembolsos", "monto_con_tasa", "tasa_x_monto"]
    g = df.groupby(["periodo", "banco", "tipo", "producto", "plazo"], as_index=False)[m].sum()
    filas = [[ix["periodos"][r.periodo], ix["bancos"][r.banco], ix["tipos"][r.tipo], ix["productos"][r.producto],
              ix["plazos"][r.plazo], round(r.monto / 1e6, 2), int(r.desembolsos), round(r.monto_con_tasa / 1e6, 2),
              round(r.tasa_x_monto / 1e6, 4)] for r in g.itertuples()]

    ultimos = dims["periodos"][-MESES_MAPA:]
    gd = df[df.periodo.isin(ultimos)].groupby(["periodo", "banco", "depto", "tipo", "producto"], as_index=False)[m].sum()
    deptos = sorted(set(gd.depto))
    filas_d = [[ix["periodos"][r.periodo], ix["bancos"][r.banco], deptos.index(r.depto), ix["tipos"][r.tipo],
                ix["productos"][r.producto], round(r.monto / 1e6, 2), round(r.monto_con_tasa / 1e6, 2),
                round(r.tasa_x_monto / 1e6, 4)] for r in gd.itertuples()]
    dims["deptos"] = [{"cod": d, "nombre": DEPARTAMENTOS.get(d, "Sin información")} for d in deptos]

    salida = {
        "meta": {"generado": datetime.now().isoformat(timespec="seconds"),
                 "ultima_fecha_corte": estado.get("ultima_fecha_corte"),
                 "parciales": estado.get("parciales", []), "huecos": estado.get("huecos", {}),
                 "fuente": "Superintendencia Financiera de Colombia · datos.gov.co (qzsc-9esp y w9zh-vetq)",
                 "entidades": "Establecimientos bancarios", "unidades": "Montos en millones de pesos; tasas E.A. en %",
                 "campos": ["periodo", "banco", "tipo", "producto", "plazo", "monto", "desembolsos", "monto_con_tasa", "tasa_x_monto"],
                 "campos_depto": ["periodo", "banco", "depto", "tipo", "producto", "monto", "monto_con_tasa", "tasa_x_monto"]},
        "dim": dims, "filas": filas, "filas_depto": filas_d,
    }
    SALIDA.write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    exportar_looker(df, g, m)
    print(f"[OK] {SALIDA.name}: {len(dims['periodos'])} meses, {len(dims['bancos'])} bancos, "
          f"{len(filas):,} filas (+{len(filas_d):,} por departamento) · {SALIDA.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
