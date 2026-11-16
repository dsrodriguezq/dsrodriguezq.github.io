"""Piezas compartidas para los reportes HTML de las automatizaciones en Python.

Cada script arma su reporte con estas funciones para que todos se vean como el portafolio:
Century Gothic, blanco y azul marino, tablas sobrias y el aviso de datos siempre visible.
"""
from html import escape
from pathlib import Path

ESTILO = """
:root{--ink:#0E1B2C;--muted:#4B5768;--line:#E3E8EF;--soft:#F5F8FB;--blue:#1C6E9E;--warn:#9A6700;--bad:#B42318;--ok:#1B7F4B}
*{box-sizing:border-box}body{margin:0;font-family:'Century Gothic',CenturyGothic,'Didact Gothic',AppleGothic,sans-serif;color:var(--ink);line-height:1.55;background:#fff}
a{color:var(--ink)}a:hover{color:var(--blue)}
.wrap{max-width:1120px;margin:0 auto;padding:0 40px}
.aviso{background:var(--ink);color:#fff;text-align:center;font-size:14px;padding:10px 16px}
header.top{display:flex;justify-content:space-between;align-items:center;padding:22px 0}
.eyebrow{margin:0 0 8px;font-size:13px;letter-spacing:.16em;color:var(--blue)}
h1{margin:0 0 12px;font-size:38px;line-height:1.15}h2{margin:44px 0 12px;font-size:24px}
.lead{margin:0;color:var(--muted);font-size:17px;max-width:760px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:16px;margin:32px 0 8px}
.kpi{border:1px solid var(--line);border-radius:6px;padding:16px 18px}
.kpi .v{font-size:26px;font-weight:700}.kpi .l{font-size:14px;color:var(--muted)}
.tabla{overflow-x:auto;border:1px solid var(--line);border-radius:6px}
table{border-collapse:collapse;width:100%;font-size:14px}
th{background:var(--soft);text-align:left;font-weight:700;padding:9px 12px;border-bottom:1px solid var(--line);white-space:nowrap}
td{padding:8px 12px;border-bottom:1px solid var(--line);vertical-align:top}
td.n,th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
tr:last-child td{border-bottom:0}
.tag{display:inline-block;font-size:12px;padding:2px 9px;border-radius:999px;background:#EEF3F8;white-space:nowrap}
.tag.bad{background:#FDECEA;color:var(--bad)}.tag.warn{background:#FFF4D6;color:var(--warn)}.tag.ok{background:#E6F4EC;color:var(--ok)}
.flujo{display:flex;flex-wrap:wrap;gap:6px;align-items:center;font-size:14px;margin:18px 0 0}
.flujo span{border:1px solid var(--line);border-radius:4px;padding:3px 10px}.flujo i{font-style:normal;color:var(--muted)}
.nota{font-size:14px;color:var(--muted)}
footer{padding:44px 0 56px;font-size:14px;color:var(--muted)}
@media(max-width:760px){.wrap{padding:0 20px}h1{font-size:30px}}
"""

LOGO = ('<svg aria-hidden="true" width="30" height="24" viewBox="0 0 30 24"><rect x="0" y="4" width="30" height="5" rx="2.5" '
        'fill="#0E1B2C"/><rect x="0" y="15" width="8" height="5" rx="2.5" fill="#1C6E9E"/></svg>')


def pesos(v, dec=0):
    """1234567.8 → $1.234.568 (formato colombiano)."""
    s = f"{abs(v):,.{dec}f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return ("-$" if v < 0 else "$") + s


def kpis(items):
    """items: lista de (valor, etiqueta)."""
    return '<div class="kpis">' + "".join(
        f'<div class="kpi"><div class="v">{escape(str(v))}</div><div class="l">{escape(l)}</div></div>' for v, l in items) + "</div>"


def tabla(columnas, filas, numericas=(), html_en=()):
    """columnas: nombres; filas: listas de valores. numericas: índices alineados a la derecha.
    html_en: índices cuyo contenido ya es HTML seguro (etiquetas)."""
    th = "".join(f'<th class="{"n" if i in numericas else ""}" scope="col">{escape(c)}</th>' for i, c in enumerate(columnas))
    cuerpo = []
    for f in filas:
        tds = "".join(
            f'<td class="{"n" if i in numericas else ""}">{v if i in html_en else escape(str(v))}</td>' for i, v in enumerate(f))
        cuerpo.append(f"<tr>{tds}</tr>")
    return f'<div class="tabla"><table><thead><tr>{th}</tr></thead><tbody>{"".join(cuerpo)}</tbody></table></div>'


def etiqueta(texto, tipo=""):
    return f'<span class="tag {tipo}">{escape(texto)}</span>'


def flujo(pasos):
    return '<div class="flujo">' + '<i>→</i>'.join(f"<span>{escape(p)}</span>" for p in pasos) + "</div>"


def pagina(destino: Path, *, titulo, eyebrow, lead, aviso, cuerpo, codigo_url, volver="../../../"):
    html = f"""<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(titulo)} · Diana Rodríguez</title><meta name="description" content="{escape(lead)}">
<link href="https://fonts.googleapis.com/css2?family=Didact+Gothic&amp;display=swap" rel="stylesheet">
<style>{ESTILO}</style></head><body>
<div class="aviso" role="note">{escape(aviso)}</div>
<div class="wrap">
<header class="top"><a href="{volver}" style="display:flex;align-items:center;gap:12px;text-decoration:none">{LOGO}
<span style="font-size:15px;letter-spacing:.22em;font-weight:700">DIANA RODRÍGUEZ</span></a>
<a href="{volver}#python" style="font-size:14px">← Volver al laboratorio</a></header>
<main><p class="eyebrow">{escape(eyebrow)}</p><h1>{escape(titulo)}</h1><p class="lead">{escape(lead)}</p>
{cuerpo}</main>
<footer>Reporte generado automáticamente por Python. <a href="{codigo_url}">Ver el código en GitHub →</a></footer>
</div></body></html>"""
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text(html, encoding="utf-8")
