"""Convierte los XML de Surefire en una tabla Markdown para el resumen de GitHub Actions."""
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

carpeta, sitio = Path(sys.argv[1]), sys.argv[2]
filas, tot = [], {"ok": 0, "fallo": 0, "omitida": 0}
for xml in sorted(carpeta.glob("TEST-*.xml")):
    suite = ET.parse(xml).getroot()
    clase = suite.get("name").split(".")[-1]
    for caso in suite.iter("testcase"):
        if caso.find("failure") is not None or caso.find("error") is not None:
            estado, clave = "❌ Falló", "fallo"
            nodo = caso.find("failure") if caso.find("failure") is not None else caso.find("error")
            detalle = (nodo.get("message") or "").splitlines()[0][:140] if nodo is not None else ""
        elif caso.find("skipped") is not None:
            estado, clave, detalle = "⏭️ Omitida", "omitida", ""
        else:
            estado, clave, detalle = "✅", "ok", ""
        tot[clave] += 1
        filas.append(f"| {clase} | {caso.get('name')} | {estado} | {float(caso.get('time', 0)):.1f} s | {detalle.replace('|', '/')} |")

print(f"## Pruebas E2E · {sitio}\n")
print(f"**{tot['ok']} aprobadas · {tot['fallo']} con fallo · {tot['omitida']} omitidas**\n")
print("| Suite | Prueba | Estado | Tiempo | Detalle |\n|---|---|---|---|---|")
print("\n".join(filas) if filas else "| — | No se generaron reportes | ❌ | | |")
