"""Cobranza de cartera automática.

1. Calcula la edad de cada factura al corte y la ubica en un tramo (al día, 1–30, 31–60, 61–90, más de 90).
2. Resume por cliente y prioriza la gestión: saldo vencido ponderado por la gravedad del tramo.
3. Redacta un correo personalizado por cliente con el tono que corresponde a su tramo.
4. Entrega el Excel de gestión y las vistas previas de los correos.

ENVIAR = False deja los correos como vista previa. Para enviarlos, se usa SMTP con variables de
entorno (nunca contraseñas en el código) o se pasa el Excel a Make, Zapier o n8n.
"""
import os
import smtplib
import sys
import unicodedata
from datetime import date, timedelta
from email.message import EmailMessage
from html import escape
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "comun"))
from reporte import etiqueta, flujo, kpis, pagina, pesos, tabla  # noqa: E402

CORTE = date(2026, 11, 15)
ENVIAR = False
TRAMOS = [("Al día", -10**6, 0), ("1–30 días", 1, 30), ("31–60 días", 31, 60), ("61–90 días", 61, 90), ("Más de 90 días", 91, 10**6)]
PESO = {"Al día": 0, "1–30 días": 1, "31–60 días": 2, "61–90 días": 3, "Más de 90 días": 4}
ACCION = {
    "1–30 días": ("Recordatorio amable", "Hola {contacto}, te escribimos para recordarte que tienes {n} {facturas} vencida{s} con nosotros. "
                  "Seguramente es un descuido; si ya hiciste el pago, por favor envíanos el soporte y actualizamos tu estado de cuenta."),
    "31–60 días": ("Segundo aviso", "Hola {contacto}, aún no registramos el pago de {n} {facturas} con más de 30 días de vencida{s}. "
                   "Te agradecemos ponerte al día esta semana. Si tienes alguna dificultad, respóndenos y buscamos una fecha que te funcione."),
    "61–90 días": ("Propuesta de acuerdo de pago", "Hola {contacto}, tu cuenta tiene {n} {facturas} con más de 60 días de mora. "
                   "Queremos ayudarte a normalizarla: podemos acordar un plan de pago en dos o tres cuotas. "
                   "Respóndenos antes del {plazo} para coordinarlo."),
    "Más de 90 días": ("Último aviso antes de cobro prejurídico", "Señor(a) {contacto}, su cuenta registra {n} {facturas} con más de 90 días de mora. "
                       "Si no recibimos el pago o una propuesta de acuerdo antes del {plazo}, el caso pasará a cobro prejurídico, "
                       "con los costos que esto implica."),
}
SEGUIMIENTO = {"1–30 días": 7, "31–60 días": 5, "61–90 días": 3, "Más de 90 días": 2}


def tramo(dias):
    return next(n for n, a, b in TRAMOS if a <= dias <= b)


def dias_habiles_despues(d, n):
    while n:
        d += timedelta(days=1)
        if d.weekday() < 5:
            n -= 1
    return d


def correo_html(c, det):
    asunto_tipo, plantilla = ACCION[c.tramo]
    n = len(det)
    texto = plantilla.format(contacto=c.contacto.split()[0] if c.tramo != "Más de 90 días" else c.contacto, n=n,
                             facturas="factura" if n == 1 else "facturas", s="" if n == 1 else "s",
                             plazo=c.seguimiento.strftime("%d/%m/%Y"))
    filas = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #E3E8EF'>{escape(f.factura)}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #E3E8EF'>{f.fecha_vencimiento:%d/%m/%Y}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #E3E8EF;text-align:right'>{f.dias_mora}</td>"
        f"<td style='padding:6px 10px;border-bottom:1px solid #E3E8EF;text-align:right'>{pesos(f.saldo)}</td></tr>"
        for f in det.itertuples())
    asunto = f"{asunto_tipo} · Estado de cuenta {c.cliente}"
    formal = c.tramo == "Más de 90 días"
    pago = ("Puede pagar por PSE o transferencia a la cuenta de ahorros 000-000000-00 de Banco Andino (ficticia), "
            f"referencia: {'su' if formal else 'tu'} NIT.")
    pago = pago if formal else pago.replace("Puede pagar", "Puedes pagar")
    cuerpo = f"""<div style="font-family:'Century Gothic',Arial,sans-serif;color:#0E1B2C;max-width:620px;line-height:1.55">
<p style="font-size:12px;color:#4B5768;margin:0 0 14px">VISTA PREVIA · DATOS FICTICIOS · NO ENVIADO</p>
<p>{escape(texto)}</p>
<table style="border-collapse:collapse;font-size:14px;width:100%;margin:14px 0">
<thead><tr style="background:#F5F8FB"><th style="text-align:left;padding:6px 10px">Factura</th><th style="text-align:left;padding:6px 10px">Venció</th>
<th style="text-align:right;padding:6px 10px">Días de mora</th><th style="text-align:right;padding:6px 10px">Saldo</th></tr></thead>
<tbody>{filas}</tbody>
<tfoot><tr><td colspan="3" style="padding:8px 10px;font-weight:700">Total vencido</td>
<td style="padding:8px 10px;text-align:right;font-weight:700">{pesos(det.saldo.sum())}</td></tr></tfoot></table>
<p>{pago}</p>
<p>Cordialmente,<br><strong>Cartera · Estudio Ceiba</strong><br>cartera@estudioceiba.ejemplo.test</p></div>"""
    return asunto, cuerpo


def enviar(para, asunto, html):
    """Solo se usa con ENVIAR=True. Credenciales desde variables de entorno SMTP_HOST, SMTP_USER y SMTP_PASS."""
    msg = EmailMessage()
    msg["From"], msg["To"], msg["Subject"] = os.environ["SMTP_USER"], para, asunto
    msg.set_content("Este correo requiere un cliente compatible con HTML.")
    msg.add_alternative(html, subtype="html")
    with smtplib.SMTP_SSL(os.environ["SMTP_HOST"], 465) as s:
        s.login(os.environ["SMTP_USER"], os.environ["SMTP_PASS"])
        s.send_message(msg)


def main():
    df = pd.read_excel(RAIZ / "datos" / "cartera_estudio_ceiba.xlsx")
    df["saldo"] = df.valor - df.abonos
    df["dias_mora"] = (pd.Timestamp(CORTE) - df.fecha_vencimiento).dt.days
    df["tramo"] = df.dias_mora.map(tramo)
    vencidas = df[df.dias_mora > 0]

    cli = df.groupby(["cliente", "contacto", "correo"], as_index=False).agg(
        saldo_total=("saldo", "sum"), facturas=("factura", "count"), max_mora=("dias_mora", "max"))
    venc = vencidas.groupby("cliente").saldo.sum().rename("saldo_vencido")
    cli = cli.merge(venc, on="cliente", how="left").fillna({"saldo_vencido": 0})
    cli["tramo"] = cli.max_mora.map(tramo)
    cli["prioridad"] = (cli.saldo_vencido * cli.tramo.map(PESO)).rank(ascending=False, method="first").astype(int)
    cli["prioridad"] = cli.prioridad.where(cli.saldo_vencido > 0).astype("Int64")
    cli["accion"] = cli.tramo.map(lambda t: ACCION[t][0] if t in ACCION else "Sin gestión")
    cli["seguimiento"] = cli.tramo.map(lambda t: dias_habiles_despues(CORTE, SEGUIMIENTO[t]) if t in SEGUIMIENTO else None)
    cli = cli.sort_values(["prioridad", "cliente"], na_position="last")

    carpeta = RAIZ / "salida" / "correos"
    carpeta.mkdir(parents=True, exist_ok=True)
    for f in carpeta.glob("*.html"):
        f.unlink()
    enlaces = {}
    for c in cli[cli.saldo_vencido > 0].itertuples():
        det = vencidas[vencidas.cliente == c.cliente].sort_values("dias_mora", ascending=False)
        asunto, html = correo_html(c, det)
        base = unicodedata.normalize("NFKD", c.cliente.lower()).encode("ascii", "ignore").decode()
        nombre = f"{int(c.prioridad):02d}_" + "".join(ch for ch in base.replace(" ", "-") if ch.isalnum() or ch == "-")[:40] + ".html"
        (carpeta / nombre).write_text(
            f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>{escape(asunto)}</title></head>"
            f"<body style='margin:24px'><p style='font-family:Arial;font-size:13px;color:#4B5768'>Para: {escape(c.correo)}<br>"
            f"Asunto: <strong>{escape(asunto)}</strong></p><hr style='border:0;border-top:1px solid #E3E8EF'>{html}</body></html>",
            encoding="utf-8")
        enlaces[c.cliente] = f"correos/{nombre}"
        if ENVIAR:
            enviar(c.correo, asunto, html)

    edades = df.groupby("tramo").saldo.sum().reindex([t for t, *_ in TRAMOS], fill_value=0)
    total = df.saldo.sum()
    with pd.ExcelWriter(RAIZ / "salida" / "gestion_cartera.xlsx", engine="openpyxl") as xw:
        cli.to_excel(xw, sheet_name="Plan de gestión", index=False)
        edades.reset_index().rename(columns={"saldo": "saldo"}).to_excel(xw, sheet_name="Edades", index=False)
        df.sort_values("dias_mora", ascending=False).to_excel(xw, sheet_name="Detalle", index=False)
        for hoja in xw.book.worksheets:
            hoja.freeze_panes = "A2"
            for col in hoja.columns:
                hoja.column_dimensions[col[0].column_letter].width = min(42, max(10, max(len(str(c.value or "")) for c in col) + 2))

    tipo = {"Al día": "ok", "1–30 días": "", "31–60 días": "warn", "61–90 días": "warn", "Más de 90 días": "bad"}
    barras = "".join(
        f"<tr><td>{t}</td><td class='n'>{pesos(v)}</td><td class='n'>{v / total:.0%}</td>"
        f"<td style='width:45%'><div style='height:10px;border-radius:0 4px 4px 0;background:#1C6E9E;width:{v / edades.max():.0%}' "
        f"title='{t}: {pesos(v)}'></div></td></tr>" for t, v in edades.items())
    tabla_edades = ('<div class="tabla"><table><thead><tr><th scope="col">Tramo</th><th class="n" scope="col">Saldo</th>'
                    f'<th class="n" scope="col">%</th><th scope="col">Distribución</th></tr></thead><tbody>{barras}</tbody></table></div>')
    gestion = cli[cli.saldo_vencido > 0]
    cuerpo = (
        flujo(["Cartera en Excel", "Edades al corte", "Priorización", "Correo según el tramo", "Plan de gestión"])
        + kpis([(pesos(total), "cartera total"), (pesos(df[df.dias_mora > 0].saldo.sum()), "vencida"),
                (f"{df[df.dias_mora > 90].saldo.sum() / total:.0%}", "con más de 90 días"),
                (len(gestion), "clientes para gestionar hoy")])
        + f"<h2>Edades de cartera al {CORTE:%d/%m/%Y}</h2>" + tabla_edades
        + "<h2>Plan de gestión priorizado</h2>"
        + tabla(["#", "Cliente", "Saldo vencido", "Mora máx.", "Tramo", "Acción", "Seguimiento", "Correo"],
                [[c.prioridad, c.cliente, pesos(c.saldo_vencido), f"{c.max_mora} d", etiqueta(c.tramo, tipo[c.tramo]), c.accion,
                  c.seguimiento.strftime("%d/%m/%Y"), f'<a href="{enlaces[c.cliente]}" style="white-space:nowrap">Ver correo</a>']
                 for c in gestion.itertuples()], numericas={2, 3}, html_en={4, 7})
        + '<p class="nota" style="margin-top:14px">Cada correo cambia de tono según el tramo: recordatorio amable, segundo aviso, '
          'propuesta de acuerdo de pago o último aviso antes de cobro prejurídico. Descarga el plan: '
          '<a href="gestion_cartera.xlsx">gestion_cartera.xlsx</a>.</p>'
    )
    pagina(RAIZ / "salida" / "reporte.html",
           titulo="Cobranza de cartera automática",
           eyebrow="PYTHON · PANDAS · CORREO HTML",
           lead="Calcula la edad de la cartera, prioriza a quién llamar primero y redacta un correo personalizado para cada cliente, "
                "con el tono que corresponde a su mora y el detalle de sus facturas.",
           aviso="Datos 100 % ficticios · clientes y correos inventados; ningún correo fue enviado",
           cuerpo=cuerpo,
           codigo_url="https://github.com/dsrodriguezq/dsrodriguezq.github.io/tree/main/proyectos/automatizaciones/python/cobranza-cartera")
    print(f"[OK] cartera {pesos(total)} · {len(gestion)} clientes a gestionar · {len(enlaces)} correos en vista previa")


if __name__ == "__main__":
    main()
