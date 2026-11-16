"""Monitor de la TRM (tasa de cambio peso–dólar) con datos oficiales.

Fuente: «Tasa de Cambio Representativa del Mercado – TRM», Superintendencia Financiera, publicada en
datos.gov.co (conjunto 32sa-8pi3, API Socrata). Cada día hábil, GitHub Actions:
  1. descarga los registros recientes y los une al histórico (datos/trm.csv);
  2. calcula variación diaria, a 30 días y el rango de 52 semanas;
  3. si el movimiento del día supera el umbral, deja una alerta (datos/alerta.md) que la acción
     convierte en un *issue* de GitHub, el cual llega por correo;
  4. regenera el reporte HTML con la gráfica.

Uso local: python trm.py            (descarga y actualiza)
           python trm.py --sin-red  (solo reconstruye el reporte con el histórico guardado)
"""
import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from html import escape
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ.parent / "comun"))
from reporte import kpis, pagina, flujo  # noqa: E402

URL = "https://www.datos.gov.co/resource/32sa-8pi3.json"
HISTORICO = RAIZ / "datos" / "trm.csv"
UMBRAL_ALERTA = 1.5  # % de variación diaria


def descargar(limite=800):
    params = {"$select": "valor,vigenciadesde", "$order": "vigenciadesde DESC", "$limit": str(limite)}
    req = urllib.request.Request(URL + "?" + urllib.parse.urlencode(params),
                                 headers={"Accept": "application/json", "User-Agent": "monitor-trm (dsrodriguezq.github.io)"})
    if os.environ.get("SOCRATA_APP_TOKEN"):
        req.add_header("X-App-Token", os.environ["SOCRATA_APP_TOKEN"])
    for intento in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                filas = json.load(r)
            break
        except Exception as e:  # noqa: BLE001
            if intento == 4:
                raise
            print(f"[reintento {intento + 1}] {e}")
            time.sleep(5 * 2 ** intento)
    df = pd.DataFrame(filas)
    df["fecha"] = pd.to_datetime(df.vigenciadesde).dt.date
    df["valor"] = df.valor.astype(float)
    return df[["fecha", "valor"]]


def pesos2(v):
    return "$" + f"{v:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def grafica(serie: pd.DataFrame) -> str:
    """Línea de los últimos 180 registros, con cuadrícula discreta y tooltip al pasar el cursor."""
    s = serie.tail(180).reset_index(drop=True)
    w, h, ml, mr, mt, mb = 1000, 320, 64, 96, 16, 32
    lo, hi = s.valor.min(), s.valor.max()
    pad = (hi - lo) * 0.08 or 10
    lo, hi = lo - pad, hi + pad
    x = lambda i: ml + i * (w - ml - mr) / max(1, len(s) - 1)  # noqa: E731
    y = lambda v: mt + (hi - v) * (h - mt - mb) / (hi - lo)  # noqa: E731
    pts = " ".join(f"{x(i):.1f},{y(v):.1f}" for i, v in enumerate(s.valor))
    crudo = (hi - lo) / 4
    mag = 10 ** math.floor(math.log10(crudo))
    paso = next(k * mag for k in (1, 2, 5, 10) if k * mag >= crudo)
    marcas = []
    v = (lo // paso + 1) * paso
    while v < hi:
        marcas.append(f'<line x1="{ml}" x2="{w - mr}" y1="{y(v):.1f}" y2="{y(v):.1f}" stroke="#E3E8EF"/>'
                      f'<text x="{ml - 8}" y="{y(v) + 4:.1f}" text-anchor="end" font-size="12" fill="#4B5768">{v:,.0f}'.replace(",", ".") + "</text>")
        v += paso
    meses = []
    for i, f in enumerate(s.fecha):
        if i == 0 or f.month != s.fecha[i - 1].month:
            nombre = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"][f.month - 1]
            meses.append(f'<text x="{x(i):.1f}" y="{h - 10}" font-size="12" fill="#4B5768">{nombre} {f:%y}</text>')
    ult = s.iloc[-1]
    datos = json.dumps([[f.isoformat(), round(v, 2)] for f, v in zip(s.fecha, s.valor)])
    return f"""
<figure style="margin:24px 0 0">
<svg id="trmSvg" viewBox="0 0 {w} {h}" role="img" aria-label="TRM diaria, últimos {len(s)} registros" style="width:100%;height:auto;display:block">
{''.join(marcas)}{''.join(meses)}
<polyline points="{pts}" fill="none" stroke="#1C6E9E" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>
<circle cx="{x(len(s) - 1):.1f}" cy="{y(ult.valor):.1f}" r="4" fill="#1C6E9E" stroke="#fff" stroke-width="2"/>
<text x="{x(len(s) - 1) + 10:.1f}" y="{y(ult.valor) + 4:.1f}" font-size="13" font-weight="700" fill="#0E1B2C">{escape(pesos2(ult.valor))}</text>
<line id="trmCruz" y1="{mt}" y2="{h - mb}" stroke="#4B5768" stroke-dasharray="3 3" visibility="hidden"/>
<circle id="trmPunto" r="5" fill="#1C6E9E" stroke="#fff" stroke-width="2" visibility="hidden"/>
<rect x="{ml}" y="{mt}" width="{w - ml - mr}" height="{h - mt - mb}" fill="transparent" id="trmZona"/>
</svg>
<div id="trmTip" role="status" style="position:absolute;pointer-events:none;background:#0E1B2C;color:#fff;font-size:13px;padding:6px 10px;border-radius:4px;display:none"></div>
<figcaption class="nota">Pesos por dólar. Fuente: Superintendencia Financiera de Colombia, vía datos.gov.co.</figcaption>
</figure>
<script>
(()=>{{const d={datos},svg=document.getElementById('trmSvg'),z=document.getElementById('trmZona'),c=document.getElementById('trmCruz'),
p=document.getElementById('trmPunto'),t=document.getElementById('trmTip');const lo={lo},hi={hi},W={w},H={h},ml={ml},mr={mr},mt={mt},mb={mb};
const X=i=>ml+i*(W-ml-mr)/Math.max(1,d.length-1),Y=v=>mt+(hi-v)*(H-mt-mb)/(hi-lo);
const f=new Intl.NumberFormat('es-CO',{{style:'currency',currency:'COP',minimumFractionDigits:2}});
z.addEventListener('mousemove',e=>{{const r=svg.getBoundingClientRect(),sx=(e.clientX-r.left)*W/r.width;
const i=Math.max(0,Math.min(d.length-1,Math.round((sx-ml)/(W-ml-mr)*(d.length-1))));const [fe,v]=d[i];
c.setAttribute('x1',X(i));c.setAttribute('x2',X(i));p.setAttribute('cx',X(i));p.setAttribute('cy',Y(v));
c.setAttribute('visibility','visible');p.setAttribute('visibility','visible');
t.style.display='block';t.textContent=fe.split('-').reverse().join('/')+' · '+f.format(v);
t.style.left=(e.pageX+14)+'px';t.style.top=(e.pageY-34)+'px';}});
z.addEventListener('mouseleave',()=>{{c.setAttribute('visibility','hidden');p.setAttribute('visibility','hidden');t.style.display='none';}});
}})();
</script>"""


def main(con_red=True):
    hist = pd.read_csv(HISTORICO, parse_dates=["fecha"]) if HISTORICO.exists() else pd.DataFrame(columns=["fecha", "valor"])
    if not hist.empty:
        hist["fecha"] = hist.fecha.dt.date
    if con_red:
        nuevo = descargar()
        hist = pd.concat([hist, nuevo]).drop_duplicates("fecha", keep="last")
    if hist.empty:
        sys.exit("No hay datos: ejecuta con red al menos una vez.")
    hist = hist.sort_values("fecha").reset_index(drop=True)
    HISTORICO.parent.mkdir(exist_ok=True)
    hist.to_csv(HISTORICO, index=False)

    ult, ant = hist.iloc[-1], hist.iloc[-2]
    var_dia = (ult.valor / ant.valor - 1) * 100
    hace30 = hist[hist.fecha <= ult.fecha - pd.Timedelta(days=30)]
    var_30 = (ult.valor / hace30.iloc[-1].valor - 1) * 100 if not hace30.empty else None
    anio = hist[hist.fecha > ult.fecha - pd.Timedelta(days=365)]
    resumen = {"fecha": ult.fecha.isoformat(), "valor": round(float(ult.valor), 2), "variacion_dia_pct": round(float(var_dia), 2),
               "variacion_30d_pct": None if var_30 is None else round(float(var_30), 2),
               "max_52s": round(float(anio.valor.max()), 2), "min_52s": round(float(anio.valor.min()), 2),
               "alerta": bool(abs(var_dia) >= UMBRAL_ALERTA), "actualizado": date.today().isoformat()}
    (RAIZ / "datos" / "resumen.json").write_text(json.dumps(resumen, ensure_ascii=False, indent=1), encoding="utf-8")

    alerta = RAIZ / "datos" / "alerta.md"
    if resumen["alerta"]:
        direccion = "subió" if var_dia > 0 else "bajó"
        alerta.write_text(f"La TRM vigente desde el {ult.fecha:%d/%m/%Y} es {pesos2(ult.valor)}: {direccion} "
                          f"{abs(var_dia):.2f} % frente al registro anterior ({pesos2(ant.valor)}). "
                          f"El umbral de alerta es {str(UMBRAL_ALERTA).replace('.', ',')} %.\n", encoding="utf-8")
    elif alerta.exists():
        alerta.unlink()

    signo = lambda v: ("+" if v > 0 else "") + f"{v:.2f} %".replace(".", ",")  # noqa: E731
    cuerpo = (
        flujo(["API datos.gov.co", "Histórico CSV", "Variaciones", "Alerta por issue", "Reporte"])
        + kpis([(pesos2(ult.valor), f"TRM vigente desde el {ult.fecha:%d/%m/%Y}"),
                (signo(var_dia), "frente al registro anterior"),
                ("—" if var_30 is None else signo(var_30), "en 30 días"),
                (f"{pesos2(resumen['min_52s'])} – {pesos2(resumen['max_52s'])}", "rango de 52 semanas")])
        + grafica(hist)
        + f'<p class="nota" style="margin-top:18px">Se actualiza sola cada día hábil con GitHub Actions. Si la TRM se mueve '
          f'{str(UMBRAL_ALERTA).replace(".", ",")} % o más en un día, se abre una alerta automática. Histórico descargable: '
          f'<a href="../datos/trm.csv">trm.csv</a> · última revisión {date.today():%d/%m/%Y}.</p>'
    )
    pagina(RAIZ / "salida" / "reporte.html",
           titulo="Monitor de la TRM",
           eyebrow="PYTHON · API · GITHUB ACTIONS",
           lead="La tasa de cambio oficial peso–dólar, descargada cada día hábil desde la fuente oficial, con su "
                "histórico, sus variaciones y una alerta automática cuando el movimiento es fuerte.",
           aviso="Datos públicos reales · TRM certificada por la Superintendencia Financiera de Colombia (datos.gov.co)",
           cuerpo=cuerpo,
           codigo_url="https://github.com/dsrodriguezq/dsrodriguezq.github.io/tree/main/proyectos/automatizaciones/python/monitor-trm")
    print(f"[OK] {len(hist)} registros · último {ult.fecha} = {ult.valor:,.2f} · var. día {var_dia:+.2f} %"
          + (" · ALERTA" if resumen["alerta"] else ""))


if __name__ == "__main__":
    main(con_red="--sin-red" not in sys.argv)
