# Funciones compartidas del informe: lectura de datos, formatos colombianos y tema de ggplot2.

suppressPackageStartupMessages({
  library(dplyr)
  library(readr)
  library(tidyr)
  library(ggplot2)
  library(scales)
  library(stringr)
})

MESES <- c("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio",
           "agosto", "septiembre", "octubre", "noviembre", "diciembre")
COL_BANCO   <- "#2a78d6"   # el banco del informe
COL_MERCADO <- "#8A94A3"   # referencia: mercado
TINTA <- "#0E1B2C"; GRIS <- "#4B5768"; LINEA <- "#E3E8EF"
FUENTE <- if ("URW Gothic" %in% systemfonts::system_fonts()$family) "URW Gothic" else "sans"

leer_mercado <- function(ruta) {
  read_csv(ruta, show_col_types = FALSE) |>
    mutate(fecha = as.Date(fecha))
}

# Tasa efectiva anual ponderada por monto: sum(tasa × monto) / sum(monto con tasa)
tasa_pond <- function(tasa_x_monto, monto_con_tasa) {
  ifelse(sum(monto_con_tasa) > 0, sum(tasa_x_monto) / sum(monto_con_tasa), NA_real_)
}

mes_largo <- function(f) paste(MESES[as.integer(format(f, "%m"))], format(f, "%Y"))
mes_corto <- function(f) paste0(str_sub(MESES[as.integer(format(f, "%m"))], 1, 3), " ", format(f, "%y"))

num_co <- function(x, dec = 0) {
  formatC(x, format = "f", digits = dec, big.mark = ".", decimal.mark = ",")
}

# Montos en millones de pesos → texto legible: "$23,02 billones", "$950,3 mil millones"
pesos_mill <- function(m) {
  case_when(
    abs(m) >= 1e6 ~ paste0("$", num_co(m / 1e6, 2), " billones"),
    abs(m) >= 1e3 ~ paste0("$", num_co(m / 1e3, 1), " mil millones"),
    TRUE          ~ paste0("$", num_co(m, 0), " millones")
  )
}
pct <- function(x, dec = 1) paste0(num_co(100 * x, dec), " %")
pp  <- function(x, dec = 2) { x <- round(x, dec); x[x == 0] <- 0; paste0(ifelse(x > 0, "+", ""), num_co(x, dec), " pp") }
signo_pct <- function(x, dec = 1) paste0(ifelse(x > 0, "+", ""), num_co(100 * x, dec), " %")

slug <- function(x) {
  x |> iconv(to = "ASCII//TRANSLIT") |> str_to_lower() |>
    str_replace_all("[^a-z0-9]+", "-") |> str_remove_all("^-|-$")
}

tema_informe <- function() {
  theme_minimal(base_family = FUENTE, base_size = 11) +
    theme(
      text = element_text(colour = TINTA),
      axis.text = element_text(colour = GRIS, size = 10),
      axis.title = element_blank(),
      panel.grid.major.x = element_blank(),
      panel.grid.minor = element_blank(),
      panel.grid.major.y = element_line(colour = LINEA, linewidth = 0.4),
      legend.position = "top", legend.justification = "left",
      legend.title = element_blank(), legend.text = element_text(colour = GRIS, size = 10),
      plot.title.position = "plot",
      plot.caption = element_text(colour = GRIS, size = 9, hjust = 0, lineheight = 1.2),
      plot.caption.position = "plot",
      plot.margin = margin(8, 16, 8, 8)
    )
}

# "A", "A y B", "A, B y C"
enumerar <- function(x) if (length(x) <= 1) x else paste(paste(head(x, -1), collapse = ", "), "y", tail(x, 1))

# Participaciones: más decimales cuando son pequeñas, para que no se lean como 0 %
pct_part <- function(x) ifelse(x < 0.01, pct(x, 2), pct(x, 1))
