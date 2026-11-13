# Sistema de Seguimiento Comercial

**Tablero en vivo:** https://dsrodriguezq.github.io/proyectos/seguimiento-comercial/

> **Proyecto de demostración con datos 100 % ficticios.** Recrea, con un banco inventado ("Banco Andino"), personas inventadas y datos generados por código, el tipo de sistema que construí en mi trabajo. No contiene información, código ni cifras de ninguna entidad real. Los correos usan el dominio reservado `bancoandino.example`, que no recibe mensajes.

## Qué hace

| Paso | Script | Resultado |
|---|---|---|
| 0 | `codigo/generar_fuentes.py` | 7 fuentes ficticias "desordenadas" en `fuentes/` (planta, presupuesto, desembolsos, radicaciones, visitas, tubo de oportunidades e histórico) |
| 1 | `codigo/pipeline.py` | Limpia, homologa productos, convierte el presupuesto de ancho a largo y cruza todo validando que ningún cruce duplique filas |
| 2 | `codigo/pronostico.py` | Indicadores por nivel (divisional, zonal, gerente + equipo, comercial), pronóstico de cierre 60 % ritmo + 40 % histórico, probabilidad de cumplir, segmentación K-Means y acción sugerida |
| 3 | `codigo/correos.py` | 45 correos personalizados con prevalidación de destinatarios, modo de prueba, vistas previas `.html`, archivos `.eml` y registro |
| 4 | `index.html` | Tablero con pestañas por nivel, filtro de producto y un agente que responde preguntas sin internet (TF-IDF + similitud de coseno) |

## Cómo ejecutarlo

```bash
pip install pandas numpy scikit-learn openpyxl
cd codigo
python ejecutar_todo.py
cd ..
python -m http.server        # abre http://localhost:8000
```

Los parámetros (fecha de corte, festivos, pesos del pronóstico, umbrales de alerta, modo de prueba) están en `codigo/config.py`.

## Tecnologías

Python · pandas · scikit-learn · openpyxl · HTML, CSS y JavaScript sin librerías (gráficas en SVG y agente propio)

---
Diana Sofía Rodríguez Díaz · [Portafolio](https://dsrodriguezq.github.io/) · [LinkedIn](https://www.linkedin.com/in/dsrodriguezd/)
