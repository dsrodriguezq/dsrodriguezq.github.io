# Genera un informe por banco (R Markdown parametrizado) y la página índice.
# Uso, desde la raíz del repositorio:  Rscript proyectos/informe-bancos-r/codigo/generar.R
#                                      Rscript proyectos/informe-bancos-r/codigo/generar.R "Banco de Occidente"

args <- commandArgs(trailingOnly = TRUE)
aqui <- normalizePath(dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE))))
setwd(aqui)
source("funciones.R")

datos  <- "../../monitor-mercado/datos/looker/credito_mensual.csv"
salida <- normalizePath("../informes", mustWork = FALSE)
dir.create(salida, showWarnings = FALSE)

df  <- leer_mercado(datos)
mes <- max(df$fecha)

resumen <- df |>
  filter(fecha == mes) |>
  group_by(banco) |>
  summarise(monto = sum(monto_millones), creditos = sum(desembolsos),
            tasa = tasa_pond(tasa_x_monto, monto_con_tasa_millones), .groups = "drop") |>
  mutate(part = monto / sum(monto)) |>
  arrange(desc(monto)) |>
  mutate(puesto = row_number(), archivo = paste0(slug(banco), ".html"))

bancos <- if (length(args)) args else resumen$banco
if (!length(args)) unlink(list.files(salida, pattern = "\\.html$", full.names = TRUE))

for (b in bancos) {
  rmarkdown::render("informe.Rmd", params = list(banco = b, datos = datos),
                    output_file = resumen$archivo[resumen$banco == b], output_dir = salida,
                    intermediates_dir = tempdir(), envir = new.env(), quiet = TRUE)
  cat("[OK]", b, "\n")
}

# ---- Página índice ----
esc <- function(x) { x <- gsub("&", "&amp;", x); x <- gsub("<", "&lt;", x); gsub(">", "&gt;", x) }
m_tasa <- with(filter(df, fecha == mes), tasa_pond(tasa_x_monto, monto_con_tasa_millones))
filas <- with(resumen, sprintf(
  '<tr><td class="n">%d</td><td><a href="%s">%s</a></td><td class="n">%s</td><td class="n">%s</td><td class="n">%s</td></tr>',
  puesto, archivo, esc(banco), pesos_mill(monto), pct_part(part), ifelse(is.na(tasa), "—", pct(tasa / 100, 2))))
css <- paste(readLines("estilo.css", warn = FALSE), collapse = "\n")
html <- sprintf('<!doctype html>
<html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Informes de crédito por banco · Diana Rodríguez</title>
<meta name="description" content="Un informe automático por cada banco de Colombia, generado con R y R Markdown a partir de datos públicos de la Superintendencia Financiera.">
<style>%s
td.n,th.n{text-align:right}</style></head><body>
<div class="aviso" role="note">Datos públicos reales · Superintendencia Financiera de Colombia vía datos.gov.co · informes generados automáticamente con R</div>
<header class="top"><a href="../../../" class="marca"><svg aria-hidden="true" width="30" height="24" viewBox="0 0 30 24"><rect x="0" y="4" width="30" height="5" rx="2.5" fill="#0E1B2C"/><rect x="0" y="15" width="8" height="5" rx="2.5" fill="#1C6E9E"/></svg><span>DIANA RODRÍGUEZ</span></a><a href="../../../#trabajo">← Volver al portafolio</a></header>
<main>
<p class="eyebrow">R · R MARKDOWN · GGPLOT2 · GITHUB ACTIONS</p>
<h1 class="titulo">Un informe de crédito para cada banco, escrito solo</h1>
<p style="max-width:760px;color:#4B5768;font-size:17px">Un solo documento de R Markdown con parámetros produce %d informes, uno por banco: indicadores, lectura del mes redactada con reglas, comparación de tasas frente al mercado y principales productos. Se regeneran cada vez que el Monitor de mercado trae datos nuevos.</p>
<div class="kpis">
<div class="kpi"><div class="v">%d</div><div class="l">informes generados</div></div>
<div class="kpi"><div class="v">%s</div><div class="l">mes con datos más reciente</div></div>
<div class="kpi"><div class="v">%s</div><div class="l">desembolsado por los bancos</div></div>
<div class="kpi"><div class="v">%s</div><div class="l">tasa ponderada E.A. del mercado</div></div>
</div>
<h2>Elige un banco</h2>
<div class="tabla-wrap"><table class="tabla"><thead><tr><th class="n" scope="col">#</th><th scope="col">Banco</th><th class="n" scope="col">Desembolsado</th><th class="n" scope="col">Participación</th><th class="n" scope="col">Tasa E.A.</th></tr></thead>
<tbody>%s</tbody></table></div>
<p class="nota" style="margin-top:16px">Cifras de %s. <a href="https://github.com/dsrodriguezq/dsrodriguezq.github.io/tree/main/proyectos/informe-bancos-r">Ver el código en GitHub →</a></p>
</main></body></html>',
  css, nrow(resumen), nrow(resumen), str_to_sentence(mes_largo(mes)), pesos_mill(sum(resumen$monto)),
  pct(m_tasa / 100, 2), paste(filas, collapse = "\n"), mes_largo(mes))
writeLines(html, file.path(salida, "index.html"), useBytes = TRUE)
cat("[OK] índice con", nrow(resumen), "bancos →", salida, "\n")
