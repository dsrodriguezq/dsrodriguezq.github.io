"""Conciliación bancaria automática: cruza el extracto del banco contra el auxiliar contable.

Reglas, en orden:
  1. Exacta: mismo valor y misma fecha.
  2. Por fecha cercana: mismo valor y hasta 3 días de diferencia (el banco registra después).
  3. Por referencia: el número de referencia coincide pero el valor no → diferencia para revisar.
Lo que sobra se clasifica (cheques y consignaciones en tránsito, notas débito y crédito por
registrar) y se arma la prueba: el saldo del banco ajustado debe igualar al de libros ajustado.
"""
import re
import sys
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "comun"))
from reporte import etiqueta, flujo, kpis, pagina, pesos, tabla  # noqa: E402

SALDO_INICIAL = 25_000_000  # saldo conciliado a 30 de septiembre, igual en banco y libros
DIAS_MAX = 3


def cargar():
    bc = pd.read_csv(RAIZ / "datos" / "extracto_banco_andino_octubre.csv", sep=";", decimal=",")
    bc["fecha"] = pd.to_datetime(bc.fecha, format="%d/%m/%Y")
    bc["ref"] = bc.descripcion.str.extract(r"(?:REF|PSE)\s+(\d{4,})", expand=False).fillna("")
    lb = pd.read_excel(RAIZ / "datos" / "auxiliar_bancos_octubre.xlsx", dtype={"referencia": str})
    lb["fecha"] = pd.to_datetime(lb.fecha)
    lb["ref"] = lb.referencia.fillna("").astype(str)
    bc["id"], lb["id"] = [f"B{i:03d}" for i in range(len(bc))], [f"L{i:03d}" for i in range(len(lb))]
    return bc.reset_index(drop=True), lb.reset_index(drop=True)


def cruzar(bc, lb):
    libres_b, libres_l = set(bc.id), set(lb.id)
    cruces = []

    def emparejar(regla, condicion, ordenar):
        for _, b in bc[bc.id.isin(libres_b)].iterrows():
            cand = lb[lb.id.isin(libres_l)]
            cand = cand[condicion(b, cand)]
            if cand.empty:
                continue
            l = cand.loc[ordenar(b, cand)]
            libres_b.discard(b.id)
            libres_l.discard(l.id)
            cruces.append({"regla": regla, "id_banco": b.id, "id_libro": l.id, "fecha_banco": b.fecha.date(),
                           "fecha_libro": l.fecha.date(), "descripcion_banco": b.descripcion,
                           "descripcion_libro": l.descripcion, "valor_banco": b.valor, "valor_libro": l.valor,
                           "diferencia": b.valor - l.valor, "dias": (b.fecha - l.fecha).days})

    emparejar("1 · Exacta", lambda b, c: (c.valor == b.valor) & (c.fecha == b.fecha), lambda b, c: c.index[0])
    emparejar("2 · Fecha cercana", lambda b, c: (c.valor == b.valor) & ((b.fecha - c.fecha).dt.days.abs() <= DIAS_MAX),
              lambda b, c: (b.fecha - c.fecha).dt.days.abs().idxmin())
    emparejar("3 · Referencia, valor distinto", lambda b, c: (b.ref != "") & (c.ref == b.ref), lambda b, c: c.index[0])
    return pd.DataFrame(cruces), bc[bc.id.isin(libres_b)].copy(), lb[lb.id.isin(libres_l)].copy()


def clasificar_banco(desc):
    d = desc.upper()
    if "GMF" in d or "COMISION" in d:
        return "Nota débito por registrar"
    if "INTERES" in d:
        return "Nota crédito por registrar"
    return "Revisar con el banco"


def clasificar_libro(fila):
    if fila.ref.startswith("CH"):
        return "Cheque en tránsito"
    if fila.valor > 0:
        return "Consignación en tránsito"
    return "Revisar en contabilidad"


def main():
    bc, lb = cargar()
    cruces, solo_b, solo_l = cruzar(bc, lb)
    solo_b["clasificacion"] = solo_b.descripcion.map(clasificar_banco)
    solo_l["clasificacion"] = solo_l.apply(clasificar_libro, axis=1)
    difs = cruces[cruces.diferencia != 0]

    saldo_banco = SALDO_INICIAL + bc.valor.sum()
    saldo_libros = SALDO_INICIAL + lb.valor.sum()
    banco_ajustado = saldo_banco + solo_l.valor.sum()
    libros_ajustado = saldo_libros + solo_b.valor.sum() + difs.diferencia.sum()
    cuadra = abs(banco_ajustado - libros_ajustado) < 1

    prueba = [
        ("Saldo según extracto", saldo_banco),
        ("(+/−) Partidas en libros que el banco aún no refleja", solo_l.valor.sum()),
        ("Saldo del banco ajustado", banco_ajustado),
        ("Saldo según libros", saldo_libros),
        ("(+/−) Notas del banco por registrar", solo_b.valor.sum()),
        ("(+/−) Corrección de diferencias de valor", difs.diferencia.sum()),
        ("Saldo de libros ajustado", libros_ajustado),
    ]

    salida = RAIZ / "salida"
    salida.mkdir(exist_ok=True)
    with pd.ExcelWriter(salida / "conciliacion_octubre_2026.xlsx", engine="openpyxl") as xw:
        pd.DataFrame(prueba, columns=["concepto", "valor"]).to_excel(xw, sheet_name="Resumen", index=False)
        cruces.to_excel(xw, sheet_name="Conciliadas", index=False)
        solo_b.drop(columns=["ref"]).to_excel(xw, sheet_name="Pendientes banco", index=False)
        solo_l.drop(columns=["ref"]).to_excel(xw, sheet_name="Pendientes libros", index=False)
        for hoja in xw.book.worksheets:
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                hoja.column_dimensions[col[0].column_letter].width = min(46, max(10, max(len(str(c.value or "")) for c in col) + 2))

    por_regla = cruces.regla.value_counts().sort_index()
    pend = pd.concat([solo_b.assign(origen="Banco"), solo_l.assign(origen="Libros")])
    tipo = {"Cheque en tránsito": "", "Consignación en tránsito": "", "Nota débito por registrar": "warn",
            "Nota crédito por registrar": "ok", "Revisar con el banco": "bad", "Revisar en contabilidad": "bad"}
    cuerpo = (
        flujo(["Extracto CSV", "Auxiliar Excel", "3 reglas de cruce", "Clasificación de pendientes", "Prueba de saldos"])
        + kpis([(f"{len(cruces)} de {len(bc)}", "movimientos del banco conciliados"),
                (len(difs), "diferencias de valor"),
                (len(pend), "partidas pendientes clasificadas"),
                ("Cuadra" if cuadra else "No cuadra", f"diferencia final {pesos(banco_ajustado - libros_ajustado)}")])
        + "<h2>Prueba de la conciliación</h2>"
        + tabla(["Concepto", "Valor"], [[c, pesos(v)] for c, v in prueba], numericas={1})
        + "<h2>Cómo se cruzó cada movimiento</h2>"
        + tabla(["Regla", "Movimientos"], [[r, n] for r, n in por_regla.items()], numericas={1})
        + "<h2>Diferencias de valor para corregir</h2>"
        + tabla(["Fecha", "Libros", "Banco", "Valor libros", "Valor banco", "Ajuste"],
                [[f"{d.fecha_libro:%d/%m/%Y}", d.descripcion_libro, d.descripcion_banco, pesos(d.valor_libro), pesos(d.valor_banco),
                  pesos(d.diferencia)] for d in difs.itertuples()], numericas={3, 4, 5})
        + "<h2>Partidas pendientes</h2>"
        + tabla(["Origen", "Fecha", "Descripción", "Valor", "Clasificación"],
                [[p.origen, f"{p.fecha:%d/%m/%Y}", p.descripcion, pesos(p.valor), etiqueta(p.clasificacion, tipo[p.clasificacion])]
                 for p in pend.sort_values(["origen", "fecha"]).itertuples()], numericas={3}, html_en={4})
        + '<p class="nota" style="margin-top:14px">Descarga el resultado: '
          '<a href="conciliacion_octubre_2026.xlsx">conciliacion_octubre_2026.xlsx</a> '
          '(Resumen, Conciliadas, Pendientes banco y Pendientes libros).</p>'
    )
    pagina(salida / "reporte.html",
           titulo="Conciliación bancaria automática",
           eyebrow="PYTHON · PANDAS · EXCEL",
           lead="Cruza el extracto del banco contra el auxiliar contable con tres reglas, clasifica lo que queda pendiente "
                "y arma la prueba de saldos. Lo que a mano toma una mañana, aquí corre en segundos.",
           aviso="Datos 100 % ficticios · «Banco Andino» y «Estudio Ceiba» son entidades inventadas",
           cuerpo=cuerpo,
           codigo_url="https://github.com/dsrodriguezq/dsrodriguezq.github.io/tree/main/proyectos/automatizaciones/python/conciliacion-bancaria")
    print(f"[OK] conciliadas {len(cruces)}/{len(bc)} · diferencias {len(difs)} · pendientes {len(pend)} · "
          f"{'CUADRA' if cuadra else 'NO CUADRA'} ({banco_ajustado - libros_ajustado:,.0f})")
    if not cuadra:
        sys.exit(1)


if __name__ == "__main__":
    main()
