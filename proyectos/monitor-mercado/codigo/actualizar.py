"""
Paso 1 · Descarga y guarda los meses de datos de tasas y desembolsos.

Uso normal (lo corre la acción de GitHub dos veces al mes):
    python actualizar.py                      # meses disponibles en el conjunto reciente
Carga hacia atrás (una sola vez, o para rellenar huecos):
    python actualizar.py --desde 2025-01      # usa el histórico grande para lo anterior
Opciones:
    --forzar        vuelve a descargar meses ya guardados
    --dias 7        tamaño inicial de cada tramo del histórico grande

Cada mes queda en datos/mensual/AAAA-MM.csv.gz, ya agregado por banco, municipio, tipo de
crédito, producto y plazo. Es idempotente: un mes completo ya guardado no se vuelve a pedir.
Un mes que todavía no termina se marca como parcial y se vuelve a descargar en la siguiente corrida.
"""
import argparse
import json
from pathlib import Path

import pandas as pd

import sfc_api as api

CARPETA = Path(__file__).resolve().parent.parent / "datos" / "mensual"
ESTADO = CARPETA / "estado.json"
PISO_DIAS = 2


def leer_estado():
    return json.loads(ESTADO.read_text(encoding="utf-8")) if ESTADO.exists() else {"parciales": [], "huecos": {}}


def guardar_mes(periodo, df):
    CARPETA.mkdir(parents=True, exist_ok=True)
    df.drop(columns=["periodo"]).to_csv(CARPETA / f"{periodo}.csv.gz", index=False, compression="gzip")
    print(f"    → {periodo}: {int(df.desembolsos.sum()):,} registros · ${df.monto.sum() / 1e12:,.2f} billones")


def tramo_adaptativo(inicio, fin, nivel=0):
    """Si un tramo no responde, se parte a la mitad y se reintenta, hasta PISO_DIAS."""
    try:
        return api.descargar(api.HISTORICO, inicio, fin), []
    except api.ErrorFuente as e:
        dias = (fin - inicio).days
        if dias <= PISO_DIAS:
            print(f"      {'  ' * nivel}[!] {inicio:%Y-%m-%d} → {fin:%Y-%m-%d} sin respuesta ({e}): queda como hueco")
            return None, [(inicio, fin)]
        mitad = inicio + (fin - inicio) / 2
        print(f"      {'  ' * nivel}[!] {inicio:%Y-%m-%d} → {fin:%Y-%m-%d} sin respuesta; se parte en dos")
        a, ha = tramo_adaptativo(inicio, mitad, nivel + 1)
        b, hb = tramo_adaptativo(mitad, fin, nivel + 1)
        piezas = [x for x in (a, b) if x is not None and len(x)]
        return (pd.concat(piezas) if piezas else None), ha + hb


def mes_historico(inicio_mes, dias):
    fin_mes = inicio_mes + pd.offsets.MonthBegin(1)
    piezas, huecos, ini = [], [], inicio_mes
    while ini < fin_mes:
        fin = min(ini + pd.Timedelta(days=dias), fin_mes)
        df, h = tramo_adaptativo(ini, fin)
        if df is not None and len(df):
            piezas.append(df)
        huecos += h
        ini = fin
    if not piezas:
        return None, huecos
    df = pd.concat(piezas).groupby(["periodo"] + api.DIMENSIONES, as_index=False)[api.METRICAS].sum()
    return df, huecos


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--desde", help="AAAA-MM: carga hacia atrás desde este mes")
    ap.add_argument("--dias", type=int, default=7)
    ap.add_argument("--forzar", action="store_true")
    args = ap.parse_args()
    estado = leer_estado()

    ini_pub, fin_pub = api.cobertura(api.RECIENTE)
    primer_reciente = ini_pub.replace(day=1)
    if ini_pub.day > 1:                      # el primer mes del conjunto reciente puede venir recortado
        primer_reciente = primer_reciente + pd.offsets.MonthBegin(1)
    print(f"Conjunto reciente: {ini_pub:%Y-%m-%d} → {fin_pub:%Y-%m-%d}")

    # 1. Carga hacia atrás con el histórico grande
    if args.desde:
        mes = pd.Timestamp(args.desde).replace(day=1)
        while mes < primer_reciente:
            periodo = f"{mes:%Y-%m}"
            if (CARPETA / f"{periodo}.csv.gz").exists() and not args.forzar and periodo not in estado["huecos"]:
                print(f"  {periodo}: ya existe")
            else:
                print(f"  {periodo}: histórico grande, tramos de {args.dias} días")
                df, huecos = mes_historico(mes, args.dias)
                if df is not None:
                    guardar_mes(periodo, df[df.periodo == periodo])
                if huecos:
                    estado["huecos"][periodo] = [f"{a:%Y-%m-%d}/{b:%Y-%m-%d}" for a, b in huecos]
                else:
                    estado["huecos"].pop(periodo, None)
                ESTADO.write_text(json.dumps(estado, indent=2), encoding="utf-8")
            mes = mes + pd.offsets.MonthBegin(1)

    # 2. Meses del conjunto reciente (incluye el mes en curso, que queda como parcial)
    mes = primer_reciente
    while mes <= fin_pub:
        periodo = f"{mes:%Y-%m}"
        fin_mes = mes + pd.offsets.MonthBegin(1)
        completo = fin_pub >= fin_mes - pd.Timedelta(days=7)    # la fuente publica cortes semanales
        ya = (CARPETA / f"{periodo}.csv.gz").exists() and periodo not in estado["parciales"]
        if ya and not args.forzar:
            print(f"  {periodo}: ya existe y está completo")
        else:
            print(f"  {periodo}: conjunto reciente{' (parcial)' if not completo else ''}")
            df = api.descargar(api.RECIENTE, mes, fin_mes)
            if len(df):
                guardar_mes(periodo, df[df.periodo == periodo])
            estado["parciales"] = sorted(set(estado["parciales"]) - {periodo} | ({periodo} if not completo else set()))
        mes = fin_mes
    estado["ultima_fecha_corte"] = f"{fin_pub:%Y-%m-%d}"
    ESTADO.write_text(json.dumps(estado, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
