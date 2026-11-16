"""Lee una carpeta de facturas electrónicas XML (UBL 2.1), las consolida y las valida.

Salidas:
- salida/facturas_consolidadas.xlsx: hojas Facturas, Líneas y Alertas, lista para contabilidad.
- salida/reporte.html: resumen visual para el portafolio.

Validaciones: DV del NIT del proveedor, IVA del encabezado = suma del IVA de las líneas,
total a pagar = base + IVA, y facturas duplicadas (mismo NIT + número, o mismo CUFE).
"""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "comun"))
from reporte import etiqueta, flujo, kpis, pagina, pesos, tabla  # noqa: E402

NS = {"i": "urn:oasis:names:specification:ubl:schema:xsd:Invoice-2",
      "cac": "urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2",
      "cbc": "urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2"}
PESOS_DV = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]
TOLERANCIA = 1  # pesos, por redondeos


def dv_correcto(nit: str) -> int:
    s = sum(int(d) * PESOS_DV[i] for i, d in enumerate(reversed(nit)))
    r = s % 11
    return r if r in (0, 1) else 11 - r


def num(nodo, ruta):
    el = nodo.find(ruta, NS)
    return float(el.text) if el is not None and el.text else 0.0


def txt(nodo, ruta):
    el = nodo.find(ruta, NS)
    return el.text.strip() if el is not None and el.text else ""


def leer(archivo: Path):
    r = ET.parse(archivo).getroot()
    prov = r.find("cac:AccountingSupplierParty/cac:Party/cac:PartyTaxScheme", NS)
    nit_el = prov.find("cbc:CompanyID", NS)
    factura = {
        "archivo": archivo.name,
        "numero": txt(r, "cbc:ID"),
        "cufe": txt(r, "cbc:UUID"),
        "fecha": txt(r, "cbc:IssueDate"),
        "vence": txt(r, "cbc:DueDate"),
        "proveedor": txt(prov, "cbc:RegistrationName"),
        "nit": nit_el.text.strip(),
        "dv": int(nit_el.get("schemeID", "-1")),
        "base": num(r, "cac:LegalMonetaryTotal/cbc:LineExtensionAmount"),
        "iva": num(r, "cac:TaxTotal/cbc:TaxAmount"),
        "total": num(r, "cac:LegalMonetaryTotal/cbc:PayableAmount"),
    }
    lineas = []
    for ln in r.findall("cac:InvoiceLine", NS):
        lineas.append({
            "archivo": archivo.name, "numero": factura["numero"], "nit": factura["nit"],
            "descripcion": txt(ln, "cac:Item/cbc:Description"),
            "cantidad": num(ln, "cbc:InvoicedQuantity"),
            "precio": num(ln, "cac:Price/cbc:PriceAmount"),
            "base": num(ln, "cbc:LineExtensionAmount"),
            "tarifa_iva": num(ln, "cac:TaxTotal/cac:TaxSubtotal/cac:TaxCategory/cbc:Percent"),
            "iva": num(ln, "cac:TaxTotal/cbc:TaxAmount"),
        })
    return factura, lineas


def validar(fact: pd.DataFrame, lin: pd.DataFrame) -> pd.DataFrame:
    alertas = []
    iva_lineas = lin.groupby("archivo").iva.sum()
    for _, f in fact.iterrows():
        ok_dv = dv_correcto(f.nit)
        if f.dv != ok_dv:
            alertas.append((f.archivo, f.numero, f.proveedor, "DV del NIT inválido",
                            f"El XML dice {f.dv}; para {f.nit} debe ser {ok_dv}. Verificar en el RUT antes de pagar."))
        esperado = iva_lineas.get(f.archivo, 0)
        if abs(f.iva - esperado) > TOLERANCIA:
            alertas.append((f.archivo, f.numero, f.proveedor, "IVA no cuadra",
                            f"Encabezado {pesos(f.iva)} vs. líneas {pesos(esperado)} (diferencia {pesos(f.iva - esperado)})."))
        if abs(f.total - (f.base + f.iva)) > TOLERANCIA:
            alertas.append((f.archivo, f.numero, f.proveedor, "Total no cuadra",
                            f"Total {pesos(f.total)} vs. base + IVA {pesos(f.base + f.iva)}."))
    dup = fact[fact.duplicated(["nit", "numero"], keep="first") | fact.duplicated("cufe", keep="first")]
    for _, f in dup.iterrows():
        alertas.append((f.archivo, f.numero, f.proveedor, "Factura duplicada",
                        "Ya se había recibido con el mismo NIT y número. No registrar ni pagar dos veces."))
    return pd.DataFrame(alertas, columns=["archivo", "numero", "proveedor", "alerta", "detalle"])


def main(carpeta: Path = RAIZ / "datos" / "xml"):
    archivos = sorted(carpeta.glob("*.xml"))
    if not archivos:
        sys.exit(f"No hay XML en {carpeta}. Ejecuta primero generar_facturas.py")
    facturas, lineas = [], []
    for a in archivos:
        f, ls = leer(a)
        facturas.append(f)
        lineas.extend(ls)
    fact, lin = pd.DataFrame(facturas), pd.DataFrame(lineas)
    alertas = validar(fact, lin)
    fact["estado"] = fact.archivo.map(lambda a: "Revisar" if a in set(alertas.archivo) else "OK")

    salida = RAIZ / "salida"
    salida.mkdir(exist_ok=True)
    with pd.ExcelWriter(salida / "facturas_consolidadas.xlsx", engine="openpyxl") as xw:
        fact.drop(columns="cufe").to_excel(xw, sheet_name="Facturas", index=False)
        lin.to_excel(xw, sheet_name="Líneas", index=False)
        alertas.to_excel(xw, sheet_name="Alertas", index=False)
        for hoja in xw.book.worksheets:
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                hoja.column_dimensions[col[0].column_letter].width = min(48, max(10, max(len(str(c.value or "")) for c in col) + 2))

    unicos = fact.drop_duplicates(["nit", "numero"])
    revisar = fact[fact.estado == "Revisar"]
    tipo_alerta = {"Factura duplicada": "bad", "DV del NIT inválido": "bad", "IVA no cuadra": "warn", "Total no cuadra": "warn"}
    cuerpo = (
        flujo(["Carpeta de XML", "Lectura UBL 2.1", "4 validaciones", "Excel consolidado", "Alertas"])
        + kpis([(len(archivos), "XML leídos"), (len(unicos), "facturas únicas"),
                (pesos(unicos.total.sum()), "total a pagar"), (len(revisar), "para revisar antes de pagar")])
        + "<h2>Alertas</h2>"
        + tabla(["Factura", "Proveedor", "Alerta", "Detalle"],
                [[a.numero, a.proveedor, etiqueta(a.alerta, tipo_alerta.get(a.alerta, "")), a.detalle] for a in alertas.itertuples()],
                html_en={2})
        + "<h2>Facturas consolidadas</h2>"
        + tabla(["Fecha", "Factura", "Proveedor", "NIT", "Base", "IVA", "Total", "Estado"],
                [[f.fecha, f.numero, f.proveedor, f"{f.nit}-{f.dv}", pesos(f.base), pesos(f.iva), pesos(f.total),
                  etiqueta(f.estado, "ok" if f.estado == "OK" else "warn")] for f in fact.sort_values("fecha").itertuples()],
                numericas={4, 5, 6}, html_en={7})
        + '<p class="nota" style="margin-top:14px">Descarga el resultado: '
          '<a href="facturas_consolidadas.xlsx">facturas_consolidadas.xlsx</a> (hojas Facturas, Líneas y Alertas).</p>'
    )
    pagina(salida / "reporte.html",
           titulo="Lector de facturas electrónicas",
           eyebrow="PYTHON · XML · PANDAS · EXCEL",
           lead="Lee una carpeta de facturas electrónicas en XML, las consolida en Excel y detecta errores antes de pagar: "
                "NIT con dígito de verificación inválido, IVA o total que no cuadran y facturas que llegan dos veces.",
           aviso="Datos 100 % ficticios · proveedores, NIT y CUFE inventados para la demostración",
           cuerpo=cuerpo,
           codigo_url="https://github.com/dsrodriguezq/dsrodriguezq.github.io/tree/main/proyectos/automatizaciones/python/facturas-dian")
    print(f"[OK] {len(archivos)} XML · {len(unicos)} facturas únicas · {len(alertas)} alertas → {salida}")


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else RAIZ / "datos" / "xml")
