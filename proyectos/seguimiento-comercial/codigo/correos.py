"""
Paso 3 · Correos de seguimiento personalizados por nivel.

Un correo por destinatario, con una sección por producto:
    Divisional          ve a sus zonales
    Cada zonal          ve a sus gerentes (con copia a ellos)
    Cada gerente de CN  ve a cada persona de su equipo (con copia a sus ejecutivos)

Cada correo trae: avance frente a lo que debía llevar al corte, pronóstico de cierre con
probabilidad, las 3 mayores brechas de colocación y de radicaciones, una acción sugerida y,
si alguien ya cumplió la meta del mes, un mensaje de reconocimiento.

Seguridad del envío:
    - Prevalidación de TODOS los destinatarios antes del primer correo. Si uno falla, no sale ninguno.
    - MODO_PRUEBA: todo se redirige al correo de prueba y solo se genera una muestra por nivel.
    - ENVIAR = False: no se envía nada; se generan vistas previas .html y archivos .eml.
    - Registro de cada correo en correos/log_envio.csv.

Los destinatarios usan el dominio reservado bancoandino.example, que no recibe correos reales.
"""
import html
import json
import re
from datetime import datetime
from email.message import EmailMessage

import pandas as pd

import config as C

PATRON_CORREO = re.compile(r"^[a-z0-9._-]+@[a-z0-9.-]+\.[a-z]+$")
TINTA, SECUNDARIO, LINEA, ACENTO, FONDO = "#0E1B2C", "#4B5768", "#E3E8EF", "#1C6E9E", "#F5F8FB"
COLOR_ALERTA = {"ALTA PROBABILIDAD": ("#E7F4EE", "#17643F"), "EN RIESGO": ("#FFF4E0", "#8A5300"),
                "BAJA PROBABILIDAD": ("#FDECEA", "#9E2A1E"), "SIN HISTORIA": ("#EEF1F4", "#4B5768")}


# --------------------------------------------------------------------------- formato
def fmt_valor(v, monetario):
    if v is None or pd.isna(v):
        return "—"
    return f"${v:,.0f} M".replace(",", ".") if monetario else f"{v:,.0f}".replace(",", ".")


def fmt_pct(v):
    return "—" if v is None or pd.isna(v) else f"{v * 100:.1f} %".replace(".", ",")


def tarjeta(titulo, valor, detalle):
    return (f'<td style="width:33%;padding:14px;border:1px solid {LINEA};background:{FONDO};vertical-align:top;">'
            f'<div style="font-size:11px;letter-spacing:.08em;color:{SECUNDARIO};">{titulo}</div>'
            f'<div style="font-size:22px;font-weight:bold;color:{TINTA};margin-top:4px;">{valor}</div>'
            f'<div style="font-size:12px;color:{SECUNDARIO};margin-top:4px;">{detalle}</div></td>')


def chip_alerta(alerta, prob):
    fondo, texto = COLOR_ALERTA.get(alerta, COLOR_ALERTA["SIN HISTORIA"])
    etiqueta = alerta.capitalize() + (f" · {fmt_pct(prob)}" if prob is not None and not pd.isna(prob) else "")
    return (f'<span style="display:inline-block;padding:3px 10px;border-radius:12px;background:{fondo};'
            f'color:{texto};font-size:12px;font-weight:bold;">{etiqueta}</span>')


def lista_top(items, monetario):
    if not items:
        return f'<li style="color:{SECUNDARIO};">Sin brechas pendientes.</li>'
    return "".join(f"<li><b>{html.escape(n)}</b>: faltan {fmt_valor(v, monetario)}</li>" for n, v in items)


def top_brechas(filas, nombre_col, campo):
    t = filas[filas[campo] > 0].nlargest(C.TOP_N, campo)
    return [(r[nombre_col], r[campo]) for _, r in t.iterrows()]


def reconocimiento_equipo(nombres, etiqueta):
    lista = ", ".join(html.escape(n) for n in nombres)
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:16px 0;">'
            f'<tr><td style="padding:18px 20px;border:1px solid {ACENTO};border-left:6px solid {ACENTO};background:#EEF5FB;">'
            f'<div style="font-size:12px;letter-spacing:.12em;color:{ACENTO};font-weight:bold;">META DEL MES CUMPLIDA · {etiqueta.upper()}</div>'
            f'<div style="font-size:17px;font-weight:bold;color:{TINTA};margin-top:6px;">{lista} ya superaron su meta del mes.</div>'
            f'<div style="font-size:14px;color:{SECUNDARIO};margin-top:4px;">Un reconocimiento a tiempo ayuda a sostener el ritmo del equipo.</div>'
            f'</td></tr></table>')


def reconocimiento(nombre, cump, etiqueta):
    return (f'<table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="margin:16px 0;">'
            f'<tr><td style="padding:18px 20px;border:1px solid {ACENTO};border-left:6px solid {ACENTO};background:#EEF5FB;">'
            f'<div style="font-size:12px;letter-spacing:.12em;color:{ACENTO};font-weight:bold;">META DEL MES CUMPLIDA</div>'
            f'<div style="font-size:20px;font-weight:bold;color:{TINTA};margin-top:6px;">{html.escape(nombre)}, ya superaste la meta de {etiqueta}.</div>'
            f'<div style="font-size:14px;color:{SECUNDARIO};margin-top:4px;">Llevas {fmt_pct(cump)} del presupuesto mensual con días hábiles por delante. ¡Gracias por marcar el paso!</div>'
            f'</td></tr></table>')


# --------------------------------------------------------------------------- secciones
def seccion_producto(prod, resumen, subordinados, nombre_col, corte):
    info = C.PRODUCTOS[prod]
    m = info["monetario"]
    r = resumen
    top_col = top_brechas(subordinados, nombre_col, "BRECHA")
    top_rad = top_brechas(subordinados, nombre_col, "BRECHA_RAD")
    visitas = (f"{r['REAL_VISITAS']:,.0f}".replace(",", "."), f"Meta mes {r['PPTO_VISITAS']:,.0f}".replace(",", ".")) \
        if r.get("PPTO_VISITAS", 0) else ("—", "Sin meta de visitas")
    return f"""
    <h3 style="font-size:16px;color:{TINTA};margin:26px 0 10px;padding-bottom:6px;border-bottom:2px solid {LINEA};">{info['etiqueta']}</h3>
    <table role="presentation" width="100%" cellspacing="8" cellpadding="0" style="border-collapse:separate;margin:0 -8px;">
      <tr>{tarjeta('COLOCACIÓN', fmt_valor(r['REAL'], m), f"Debía llevar {fmt_valor(r['PPTO_CORTE'], m)} · {fmt_pct(r['CUMP_CORTE'])} al corte")}
          {tarjeta('RADICACIONES', f"{r['REAL_RADICACIONES']:,.0f}".replace(',', '.'), f"Meta mes {r['PPTO_RADICACIONES']:,.0f}".replace(',', '.') + f" · {fmt_pct(r['CUMP_RAD_CORTE'])} al corte")}
          {tarjeta('VISITAS', *visitas)}</tr>
    </table>
    <p style="margin:12px 0;font-size:14px;color:{TINTA};">Pronóstico de cierre: <b>{fmt_valor(r['PRON_REAL'], m)}</b>
      ({fmt_pct(r['PRON_CUMP'])} de la meta de {fmt_valor(r['PPTO'], m)}) &nbsp;{chip_alerta(r['ALERTA'], r['PROB'])}<br>
      <span style="color:{SECUNDARIO};font-size:13px;">Para cumplir faltan {fmt_valor(r['BRECHA'], m)}: {fmt_valor(r['META_DIARIA'], m)} por cada uno de los {corte['dias_restantes']} días hábiles que quedan.</span></p>
    <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="font-size:13px;border-collapse:collapse;">
      <tr style="background:{FONDO};"><td style="padding:9px;width:50%;"><b>Mayores brechas de colocación</b></td><td style="padding:9px;"><b>Mayores brechas de radicaciones</b></td></tr>
      <tr><td style="padding:9px;vertical-align:top;"><ul style="margin:0;padding-left:18px;">{lista_top(top_col, m)}</ul></td>
          <td style="padding:9px;vertical-align:top;"><ul style="margin:0;padding-left:18px;">{lista_top(top_rad, False)}</ul></td></tr>
    </table>"""


def cuerpo(nombre, titulo, secciones_html, reconocimientos, foco, corte):
    fecha = datetime.fromisoformat(corte["fecha_corte"]).strftime("%d/%m/%Y")
    return f"""<div style="font-family:'Century Gothic',CenturyGothic,Arial,sans-serif;color:{TINTA};max-width:760px;margin:0 auto;line-height:1.5;">
  <div style="background:{TINTA};color:#FFFFFF;padding:20px 24px;">
    <div style="font-size:12px;letter-spacing:.16em;opacity:.8;">BANCO ANDINO · SEGUIMIENTO COMERCIAL</div>
    <div style="font-size:20px;font-weight:bold;margin-top:4px;">{html.escape(titulo)}</div>
    <div style="font-size:12px;opacity:.85;margin-top:4px;">Corte {fecha} · día hábil {corte['dias_transcurridos']} de {corte['dias_mes']}</div>
  </div>
  <div style="padding:22px 24px;border:1px solid {LINEA};border-top:0;">
    <p style="margin-top:0;">Hola, {html.escape(nombre.split()[0])}:</p>
    {''.join(reconocimientos)}
    <p>Este es el avance de tu equipo al corte, con el pronóstico de cierre y las brechas que más pesan.</p>
    {''.join(secciones_html)}
    <p style="margin-top:22px;padding:12px 14px;background:{FONDO};border-left:4px solid {ACENTO};"><b>Foco sugerido:</b> {foco}</p>
    <p>El detalle por persona está en el <a href="https://dsrodriguezq.github.io/proyectos/seguimiento-comercial/" style="color:{ACENTO};">tablero de seguimiento</a>.</p>
    <p style="font-size:11px;color:{SECUNDARIO};margin-bottom:0;">Correo generado automáticamente · {C.BANCO} · datos 100 % ficticios para demostración.</p>
  </div>
</div>"""


# --------------------------------------------------------------------------- correos por nivel
def correos(datos):
    corte = datos["meta"]["corte"]
    div = pd.DataFrame(datos["divisional"])
    zon = pd.DataFrame(datos["zonales"])
    uni = pd.DataFrame(datos["unidades"])
    com = pd.DataFrame(datos["comerciales"])
    salida = []

    # Divisional
    d = datos["meta"]["divisional"]
    secciones = [seccion_producto(p, div[div.PRODUCTO == p].iloc[0], zon[zon.PRODUCTO == p], "ZONA", corte) for p in C.PRODUCTOS]
    peor = zon[zon.PRODUCTO == "PRESTAMO PERSONAL"].nsmallest(3, "PROB").ZONA.tolist()
    salida.append({"nivel": "DIVISIONAL", "responsable": d["nombre"], "para": d["correo"], "cc": "",
                   "asunto": "Seguimiento comercial divisional",
                   "html": cuerpo(d["nombre"], "Seguimiento comercial divisional", secciones, [],
                                  f"las zonas con menor probabilidad de cumplir en préstamo son {', '.join(peor)}. "
                                  "Conviene revisar con sus zonales el plan diario de los próximos días.", corte)})

    # Zonales: copia a los gerentes de su zona
    for zona in sorted(zon.ZONA.unique()):
        fz = zon[zon.ZONA == zona]
        nombre, correo = fz.iloc[0].NOMBRE_ZONAL, fz.iloc[0].CORREO
        uz = uni[uni.ZONA == zona]
        secciones = [seccion_producto(p, fz[fz.PRODUCTO == p].iloc[0], uz[uz.PRODUCTO == p], "NOMBRE", corte) for p in C.PRODUCTOS]
        cc = ";".join(sorted(uz.CORREO.unique()))
        critico = uz[uz.PRODUCTO == "PRESTAMO PERSONAL"].nlargest(1, "BRECHA")
        foco = (f"conversar hoy con {critico.iloc[0].NOMBRE}, que concentra la mayor brecha de préstamo, "
                "y acordar la meta diaria de cada gerente.") if len(critico) else "mantener el ritmo de todo el equipo."
        reconoc = [reconocimiento_equipo(ya, C.PRODUCTOS[p]["etiqueta"]) for p in C.PRODUCTOS
                   if (ya := uz[(uz.PRODUCTO == p) & (uz.CUMP_MES >= 1)].NOMBRE.tolist())]
        salida.append({"nivel": "ZONAL", "responsable": nombre, "para": correo, "cc": cc,
                       "asunto": f"Seguimiento comercial · Zona {zona}",
                       "html": cuerpo(nombre, f"Seguimiento comercial · Zona {zona}", secciones, reconoc, foco, corte)})

    # Gerentes de centro de negocio: ven a cada persona de su equipo
    for _, g in uni[(uni.CARGO == "GTE CN")].drop_duplicates("CODIGO_UNIDAD").iterrows():
        equipo = com[(com.CODIGO_GERENTE_CN == g.CODIGO_UNIDAD) | (com.CODIGO == g.CODIGO_UNIDAD)]
        secciones, reconoc = [], []
        for p in C.PRODUCTOS:
            fila = uni[(uni.CODIGO_UNIDAD == g.CODIGO_UNIDAD) & (uni.PRODUCTO == p)].iloc[0]
            secciones.append(seccion_producto(p, fila, equipo[equipo.PRODUCTO == p], "NOMBRE", corte))
            if fila.CUMP_MES >= 1:
                reconoc.append(reconocimiento(g.NOMBRE, fila.CUMP_MES, C.PRODUCTOS[p]["etiqueta"]))
            else:
                ya = equipo[(equipo.PRODUCTO == p) & (equipo.CUMP_MES >= 1)].NOMBRE.tolist()
                if ya:
                    reconoc.append(reconocimiento_equipo(ya, C.PRODUCTOS[p]["etiqueta"]))
        ejecutivos = com[(com.CODIGO_GERENTE_CN == g.CODIGO_UNIDAD) & (com.CARGO == "EJECUTIVO")]
        cc = ";".join(sorted(set(_correo_de(datos, c) for c in ejecutivos.CODIGO)))
        foco = g.ACCION[0].lower() + g.ACCION[1:]
        salida.append({"nivel": "GERENTE CN", "responsable": g.NOMBRE, "para": g.CORREO, "cc": cc,
                       "asunto": f"Seguimiento comercial · Equipo de {g.NOMBRE}",
                       "html": cuerpo(g.NOMBRE, f"Seguimiento comercial · Equipo de {g.NOMBRE}", secciones, reconoc, foco, corte)})
    return salida


_CORREOS = None


def _correo_de(datos, codigo):
    global _CORREOS
    if _CORREOS is None:
        p = pd.read_csv(C.CARPETA_DATOS / "personas.csv", dtype={"CODIGO": str})
        _CORREOS = dict(zip(p.CODIGO, p.CORREO))
    return _CORREOS.get(codigo, "")


# --------------------------------------------------------------------------- validación y envío
def prevalidar(lista):
    """Revisa todos los destinatarios antes de enviar. Un error cancela el envío completo."""
    errores, filas, vistos = [], [], {}
    for c in lista:
        problemas = []
        direcciones = [c["para"]] + [x for x in c["cc"].split(";") if x]
        for d in direcciones:
            if not PATRON_CORREO.match(d):
                problemas.append(f"correo inválido: {d!r}")
        if c["nivel"] == "ZONAL" and not c["cc"]:
            problemas.append("zonal sin gerentes en copia")
        if c["para"] in vistos:
            problemas.append(f"destinatario repetido con {vistos[c['para']]}")
        vistos[c["para"]] = c["responsable"]
        filas.append({"NIVEL": c["nivel"], "RESPONSABLE": c["responsable"], "PARA": c["para"], "CC": c["cc"],
                      "ESTADO": "ERROR" if problemas else "OK", "DETALLE": "; ".join(problemas)})
        if problemas:
            errores.append(f"{c['nivel']} / {c['responsable']}: {'; '.join(problemas)}")
    pd.DataFrame(filas).to_csv(C.CARPETA_CORREOS / "validacion_destinatarios.csv", index=False, encoding="utf-8-sig")
    if errores:
        raise SystemExit("Prevalidación fallida, no se envió ningún correo:\n - " + "\n - ".join(errores))
    print(f"[OK] Prevalidación aprobada: {len(lista)} correos")


def vista_previa(c):
    """Página que muestra el correo con sus encabezados, como se vería en la bandeja."""
    cab = (f'<div style="font-family:Arial,sans-serif;font-size:13px;color:#4B5768;max-width:760px;margin:24px auto 12px;line-height:1.7;">'
           f'<div style="background:#FFF4E0;color:#8A5300;padding:8px 12px;border-radius:4px;margin-bottom:10px;">'
           f'Vista previa de demostración: datos y destinatarios 100 % ficticios.</div>'
           f'<b>Para:</b> {html.escape(c["para"])}<br><b>CC:</b> {html.escape(c["cc"].replace(";", "; ")) or "—"}<br>'
           f'<b>Asunto:</b> {html.escape(c["asunto"])}</div>')
    return f'<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{html.escape(c["asunto"])}</title></head><body style="margin:0;background:#EEF1F4;padding:8px 12px 40px;">{cab}<div style="background:#fff;max-width:760px;margin:0 auto;">{c["html"]}</div></body></html>'


def nombre_archivo(c):
    base = re.sub(r"[^a-z0-9]+", "-", f"{c['nivel']}-{c['responsable']}".lower().translate(str.maketrans("áéíóúñ", "aeioun")))
    return base.strip("-")


def main():
    C.CARPETA_CORREOS.mkdir(exist_ok=True)
    datos = json.loads((C.CARPETA_DATOS / "consolidado.json").read_text(encoding="utf-8"))
    lista = correos(datos)
    prevalidar(lista)
    if C.MODO_PRUEBA:   # una muestra por nivel, todo al correo de prueba
        muestras = {}
        for c in lista:
            muestras.setdefault(c["nivel"], c)
        lista = [dict(c, para=C.CORREO_PRUEBA, cc="", asunto="[PRUEBA] " + c["asunto"]) for c in muestras.values()]
    log, indice = [], []
    for c in lista:
        archivo = nombre_archivo(c)
        (C.CARPETA_CORREOS / f"{archivo}.html").write_text(vista_previa(c), encoding="utf-8")
        msg = EmailMessage()
        msg["From"], msg["To"], msg["Subject"] = f"seguimiento@{C.DOMINIO_CORREO}", c["para"], c["asunto"]
        if c["cc"]:
            msg["Cc"] = c["cc"]
        msg.set_content("Este correo requiere un cliente que muestre HTML.")
        msg.add_alternative(c["html"], subtype="html")
        if C.ENVIAR:
            raise NotImplementedError("Conecta aquí tu servidor SMTP u Outlook. En la demostración no se envía nada.")
        (C.CARPETA_CORREOS / f"{archivo}.eml").write_bytes(bytes(msg))
        log.append({"FECHA": datetime.now().strftime("%Y-%m-%d %H:%M"), "NIVEL": c["nivel"], "RESPONSABLE": c["responsable"],
                    "PARA": c["para"], "CC": c["cc"], "ESTADO": "VISTA PREVIA"})
        indice.append({"nivel": c["nivel"], "responsable": c["responsable"], "archivo": f"correos/{archivo}.html",
                       "reconocimiento": "META DEL MES CUMPLIDA" in c["html"]})
    pd.DataFrame(log).to_csv(C.CARPETA_CORREOS / "log_envio.csv", index=False, encoding="utf-8-sig")
    (C.CARPETA_CORREOS / "indice.json").write_text(json.dumps(indice, ensure_ascii=False), encoding="utf-8")
    print(f"[OK] {len(lista)} correos generados en {C.CARPETA_CORREOS.name}/ (modo prueba: {C.MODO_PRUEBA})")


if __name__ == "__main__":
    main()
