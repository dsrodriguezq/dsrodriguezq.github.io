# Monitor de tasas y desembolsos

**Tablero en vivo:** https://dsrodriguezq.github.io/proyectos/monitor-mercado/

Monitor del mercado de crédito de los bancos en Colombia con **datos públicos reales** de la Superintendencia Financiera, publicados en [datos.gov.co](https://www.datos.gov.co). Se actualiza solo con GitHub Actions los días 6 y 21 de cada mes. Es un análisis independiente: no representa la posición de ninguna entidad.

## Qué muestra

- **Mercado:** monto desembolsado, tasa ponderada, participación y tasa del banco elegido frente al mercado, top 10 del mes y alertas de tasas.
- **Bancos mes a mes:** tasa y monto de los 15 bancos más grandes en los últimos 12 meses.
- **Plazos:** a qué plazos presta cada banco y a qué tasa (efectiva anual o nominal mes vencido).
- **Regiones:** mapa por departamento con la participación del banco, la tasa del mercado o la diferencia de tasa.
- **Posicionamiento:** quién cobra más caro y aun así gana mercado.
- **Interanual:** el mismo mes en años anteriores.
- **Micro IA:** resumen automático de lo que cambió y acciones sugeridas para el banco elegido.

## Cómo funciona

| Paso | Archivo | Qué hace |
|---|---|---|
| 1 | `codigo/sfc_api.py` | Cliente de la API: reintentos ante errores pasajeros, paginación sin orden estable con descarte de filas repetidas, solo establecimientos bancarios |
| 2 | `codigo/actualizar.py` | Descarga los meses del conjunto reciente (`qzsc-9esp`) y, con `--desde AAAA-MM`, carga hacia atrás con el histórico (`w9zh-vetq`) en tramos que se parten a la mitad si no responden. Marca meses parciales y huecos |
| 3 | `codigo/construir.py` | Une los meses, agrupa plazos, abrevia nombres de bancos, saca el departamento del código DIVIPOLA y genera `datos/mercado.json` |
| 4 | `.github/workflows/monitor-mercado.yml` | Corre los pasos 2 y 3 en GitHub y guarda los datos en el repositorio |
| 5 | `index.html` | Tablero, alertas y Micro IA, calculados en el navegador |

## Ejecutarlo en tu equipo

```bash
pip install pandas requests
cd codigo
python actualizar.py                 # meses recientes
python actualizar.py --desde 2025-01 # carga hacia atrás (puede tardar)
python construir.py
cd ..
python -m http.server                # abre http://localhost:8000
```

Opcional: una clave gratuita de datos.gov.co en la variable `SOCRATA_APP_TOKEN` sube el límite de peticiones. En GitHub se guarda como secreto del repositorio con ese mismo nombre.

---
Diana Sofía Rodríguez Díaz · [Portafolio](https://dsrodriguezq.github.io/) · [LinkedIn](https://www.linkedin.com/in/dsrodriguezd/)

## Datos para Looker Studio y Google Sheets

Cada vez que corre la acción, `construir.py` también genera dos CSV planos en `datos/looker/` (montos en millones de pesos):

- `credito_mensual.csv`: fecha, banco, tipo, producto, plazo, monto, desembolsos y los campos para la tasa.
- `credito_departamento.csv`: fecha, banco, departamento, país, tipo y las mismas métricas.

En Google Sheets se cargan solos y se mantienen al día con:

```
=IMPORTDATA("https://raw.githubusercontent.com/dsrodriguezq/dsrodriguezq.github.io/main/proyectos/monitor-mercado/datos/looker/credito_mensual.csv")
```

Tasa ponderada en Looker Studio: `SUM(tasa_x_monto) / SUM(monto_con_tasa_millones)`.
