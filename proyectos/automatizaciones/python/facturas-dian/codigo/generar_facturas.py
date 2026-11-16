"""Genera facturas electrónicas FICTICIAS en XML (estructura UBL 2.1 simplificada, como las de la DIAN).

Todo es inventado: proveedores, NIT, CUFE y valores. Cuatro facturas traen errores a propósito
para que el lector los detecte: dígito de verificación (DV) del NIT inválido, IVA que no cuadra,
total que no cuadra y una factura duplicada.
"""
import hashlib
import random
from datetime import date, timedelta
from pathlib import Path
from xml.sax.saxutils import escape

SALIDA = Path(__file__).resolve().parents[1] / "datos" / "xml"
PESOS_DV = [3, 7, 13, 17, 19, 23, 29, 37, 41, 43, 47, 53, 59, 67, 71]

PROVEEDORES = [
    "Papelería El Samán S.A.S.", "Tecnored Andina S.A.S.", "Café de la Montaña Ltda.",
    "Aseo Integral Pacífico S.A.S.", "Transportes Río Cauca S.A.S.", "Software Guadua S.A.S.",
]
PRODUCTOS = {
    "Papelería El Samán S.A.S.": [("Resma papel carta", 21900, 19), ("Carpeta legajadora", 3500, 19), ("Tóner impresora", 189000, 19)],
    "Tecnored Andina S.A.S.": [("Soporte técnico mensual", 850000, 19), ("Cable de red Cat 6 (m)", 2800, 19)],
    "Café de la Montaña Ltda.": [("Café tostado 500 g", 24000, 5), ("Azúcar 1 kg", 4800, 5)],
    "Aseo Integral Pacífico S.A.S.": [("Servicio de aseo semanal", 420000, 19), ("Desinfectante 4 L", 36000, 19)],
    "Transportes Río Cauca S.A.S.": [("Flete Cali–Palmira", 310000, 0), ("Cargue y descargue", 90000, 19)],
    "Software Guadua S.A.S.": [("Licencia ERP mensual", 1250000, 19), ("Capacitación (hora)", 120000, 19)],
}


def dv(nit: str) -> int:
    s = sum(int(d) * PESOS_DV[i] for i, d in enumerate(reversed(nit)))
    r = s % 11
    return r if r in (0, 1) else 11 - r


def xml_factura(numero, prov, nit, dv_nit, fecha, lineas, iva_doc=None, total_doc=None):
    base = sum(c * p for _, p, _, c in lineas)
    iva = sum(round(c * p * t / 100) for _, p, t, c in lineas)
    iva_doc = iva if iva_doc is None else iva_doc
    total_doc = base + iva_doc if total_doc is None else total_doc
    cufe = hashlib.sha384(f"{numero}{nit}{fecha}{total_doc}".encode()).hexdigest()
    filas = []
    for i, (desc, precio, tasa, cant) in enumerate(lineas, 1):
        sub = cant * precio
        filas.append(f"""  <cac:InvoiceLine>
    <cbc:ID>{i}</cbc:ID>
    <cbc:InvoicedQuantity unitCode="94">{cant}</cbc:InvoicedQuantity>
    <cbc:LineExtensionAmount currencyID="COP">{sub:.2f}</cbc:LineExtensionAmount>
    <cac:TaxTotal>
      <cbc:TaxAmount currencyID="COP">{round(sub * tasa / 100):.2f}</cbc:TaxAmount>
      <cac:TaxSubtotal><cac:TaxCategory><cbc:Percent>{tasa:.2f}</cbc:Percent><cac:TaxScheme><cbc:ID>01</cbc:ID><cbc:Name>IVA</cbc:Name></cac:TaxScheme></cac:TaxCategory></cac:TaxSubtotal>
    </cac:TaxTotal>
    <cac:Item><cbc:Description>{escape(desc)}</cbc:Description></cac:Item>
    <cac:Price><cbc:PriceAmount currencyID="COP">{precio:.2f}</cbc:PriceAmount></cac:Price>
  </cac:InvoiceLine>""")
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<!-- FACTURA FICTICIA generada para demostración. No tiene validez tributaria. -->
<Invoice xmlns="urn:oasis:names:specification:ubl:schema:xsd:Invoice-2"
         xmlns:cac="urn:oasis:names:specification:ubl:schema:xsd:CommonAggregateComponents-2"
         xmlns:cbc="urn:oasis:names:specification:ubl:schema:xsd:CommonBasicComponents-2">
  <cbc:UBLVersionID>UBL 2.1</cbc:UBLVersionID>
  <cbc:ID>{numero}</cbc:ID>
  <cbc:UUID schemeName="CUFE-SHA384">{cufe}</cbc:UUID>
  <cbc:IssueDate>{fecha.isoformat()}</cbc:IssueDate>
  <cbc:DueDate>{(fecha + timedelta(days=30)).isoformat()}</cbc:DueDate>
  <cbc:DocumentCurrencyCode>COP</cbc:DocumentCurrencyCode>
  <cac:AccountingSupplierParty><cac:Party><cac:PartyTaxScheme>
    <cbc:RegistrationName>{escape(prov)}</cbc:RegistrationName>
    <cbc:CompanyID schemeAgencyID="195" schemeID="{dv_nit}" schemeName="31">{nit}</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:Party></cac:AccountingSupplierParty>
  <cac:AccountingCustomerParty><cac:Party><cac:PartyTaxScheme>
    <cbc:RegistrationName>Estudio Ceiba S.A.S. (ficticio)</cbc:RegistrationName>
    <cbc:CompanyID schemeID="{dv('901555123')}" schemeName="31">901555123</cbc:CompanyID>
  </cac:PartyTaxScheme></cac:Party></cac:AccountingCustomerParty>
  <cac:TaxTotal><cbc:TaxAmount currencyID="COP">{iva_doc:.2f}</cbc:TaxAmount></cac:TaxTotal>
  <cac:LegalMonetaryTotal>
    <cbc:LineExtensionAmount currencyID="COP">{base:.2f}</cbc:LineExtensionAmount>
    <cbc:TaxExclusiveAmount currencyID="COP">{base:.2f}</cbc:TaxExclusiveAmount>
    <cbc:TaxInclusiveAmount currencyID="COP">{base + iva_doc:.2f}</cbc:TaxInclusiveAmount>
    <cbc:PayableAmount currencyID="COP">{total_doc:.2f}</cbc:PayableAmount>
  </cac:LegalMonetaryTotal>
{chr(10).join(filas)}
</Invoice>
"""


def main():
    rnd = random.Random(2026)
    SALIDA.mkdir(parents=True, exist_ok=True)
    for f in SALIDA.glob("*.xml"):
        f.unlink()
    nits = {}
    for p in PROVEEDORES:
        n = str(rnd.randint(900100000, 901899999))
        nits[p] = (n, dv(n))
    inicio = date(2026, 10, 1)
    archivos = []
    for i in range(12):
        prov = PROVEEDORES[i % len(PROVEEDORES)]
        prefijo = "".join(w[0] for w in prov.split()[:2]).upper()
        numero = f"{prefijo}{1000 + i * 7}"
        lineas = [(d, p, t, rnd.randint(1, 4)) for d, p, t in rnd.sample(PRODUCTOS[prov], k=min(2, len(PRODUCTOS[prov])))]
        nit, dvn = nits[prov]
        extra = {}
        if i == 3:   # DV del NIT equivocado
            dvn = (dvn + 3) % 10
        if i == 6:   # el IVA del encabezado no coincide con las líneas
            extra["iva_doc"] = sum(round(c * p * t / 100) for _, p, t, c in lineas) + 15000
        if i == 9:   # el total a pagar no cuadra con base + IVA
            base = sum(c * p for _, p, _, c in lineas)
            extra["total_doc"] = base + sum(round(c * p * t / 100) for _, p, t, c in lineas) - 50000
        fecha = inicio + timedelta(days=i * 2 + 1)
        xml = xml_factura(numero, prov, nit, dvn, fecha, lineas, **extra)
        nombre = f"fv_{nit}_{numero}.xml"
        (SALIDA / nombre).write_text(xml, encoding="utf-8")
        archivos.append((nombre, xml))
    # La misma factura llega dos veces, por correo y por el portal del proveedor
    nombre, xml = archivos[4]
    (SALIDA / nombre.replace(".xml", "_reenvio.xml")).write_text(xml, encoding="utf-8")
    print(f"[OK] {len(list(SALIDA.glob('*.xml')))} XML ficticios en {SALIDA}")


if __name__ == "__main__":
    main()
