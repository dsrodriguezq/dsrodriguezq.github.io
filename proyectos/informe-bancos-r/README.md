# Un informe de crédito para cada banco · R + R Markdown

> **Datos públicos reales:** Superintendencia Financiera de Colombia vía datos.gov.co, los mismos que descarga el [Monitor de mercado](../monitor-mercado/).

Un solo documento de R Markdown con parámetros (`params$banco`) produce un informe por cada banco del país. Cada informe incluye:

- **Indicadores del mes:** monto desembolsado, variación mensual, participación y puesto, y tasa ponderada frente al mercado.
- **Lectura del mes:** texto redactado con reglas. Por ejemplo, un tipo de crédito se marca como «más caro que el mercado» cuando la diferencia supera 2 puntos y pesa al menos el 5 % del banco.
- **Tres gráficas en ggplot2:** participación mes a mes, tasa por tipo de crédito frente al mercado y composición de lo que presta.
- **Tabla de los principales productos,** con la participación del banco en cada uno y su diferencia de tasa.

Además genera una página índice con todos los bancos ordenados por monto.

## Estructura

| Archivo | Para qué |
|---|---|
| `codigo/informe.Rmd` | La plantilla parametrizada del informe |
| `codigo/funciones.R` | Formatos colombianos (`$23,02 billones`, `18,58 %`), tasa ponderada y tema de ggplot2 |
| `codigo/generar.R` | Recorre los bancos, produce un HTML por cada uno y arma el índice |
| `codigo/estilo.css` | Estilo del portafolio |
| `informes/` | Resultado publicado |

## Automatización

`.github/workflows/informe-bancos-r.yml` instala R y vuelve a generar los informes cada vez que termina con éxito el Monitor de mercado (días 6 y 21 de cada mes), o cuando cambia el código.

## Correrlo

```bash
# Ubuntu: sudo apt install r-base-core pandoc r-cran-rmarkdown r-cran-ggplot2 r-cran-dplyr r-cran-readr r-cran-tidyr r-cran-scales r-cran-stringr r-cran-ragg
Rscript proyectos/informe-bancos-r/codigo/generar.R                         # todos los bancos
Rscript proyectos/informe-bancos-r/codigo/generar.R "Banco de Occidente"    # uno solo
```

La tasa ponderada se calcula como `sum(tasa × monto) / sum(monto con tasa)`. La tasa total de un banco depende de su mezcla de productos, por eso la comparación justa se hace por tipo de crédito.
