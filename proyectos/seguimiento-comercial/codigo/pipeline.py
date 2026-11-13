"""
Paso 1 · Pipeline de consolidación.

Lee las 7 fuentes ficticias de fuentes/, las limpia y las cruza en una base maestra
con una fila por comercial y producto. Antes y después de cada cruce valida que no se
dupliquen filas: si un cruce multiplica registros, el proceso se detiene.

Reglas:
  - No se inventan datos: si una métrica no existe para un comercial, queda en cero o nula
    según su naturaleza, y se reporta en el control de calidad.
  - Los códigos se normalizan como texto (sin ".0", sin espacios).
  - Los productos se homologan a un nombre canónico.
  - Los préstamos se expresan en millones de pesos; las tarjetas, en unidades.

Salidas en datos/:
  personas.csv          planta limpia (incluye divisional y zonales)
  base_maestra.csv      comercial × producto con todas las métricas del mes
  historico_limpio.csv  real y presupuesto mensual enero-octubre
  calidad.json          resumen de controles y advertencias
"""
import json
import unicodedata

import numpy as np
import pandas as pd

import config as C

ADVERTENCIAS = []


def log(msg, nivel="OK"):
    print(f"[{nivel}] {msg}")
    if nivel == "ADVERTENCIA":
        ADVERTENCIAS.append(msg)


# --------------------------------------------------------------------------- utilidades
def normalizar_texto(valor) -> str:
    texto = "" if valor is None or (isinstance(valor, float) and np.isnan(valor)) else str(valor)
    texto = "".join(c for c in unicodedata.normalize("NFD", texto.upper()) if unicodedata.category(c) != "Mn")
    return " ".join(texto.replace("_", " ").split())


def normalizar_codigo(valor) -> str:
    texto = str(valor).strip()
    if texto.endswith(".0"):
        texto = texto[:-2]
    return texto if texto not in ("", "NAN", "nan", "None") else ""


def limpiar_encabezados(df):
    df.columns = [normalizar_texto(c) for c in df.columns]
    return df


def buscar_columna(df, opciones, obligatoria=True):
    """Devuelve la primera columna cuyo nombre normalizado coincide con alguna opción."""
    indice = {normalizar_texto(c): c for c in df.columns}
    for opcion in opciones:
        if normalizar_texto(opcion) in indice:
            return indice[normalizar_texto(opcion)]
    if obligatoria:
        raise ValueError(f"No se encontró ninguna de las columnas {opciones}. Disponibles: {list(df.columns)}")
    return None


_NO_RECONOCIDOS = set()


def homologar_producto(valor) -> str:
    clave = normalizar_texto(valor)
    if clave in C.HOMOLOGACION_PRODUCTOS:
        return C.HOMOLOGACION_PRODUCTOS[clave]
    if clave not in _NO_RECONOCIDOS:          # avisa una sola vez por variante
        _NO_RECONOCIDOS.add(clave)
        log(f"Producto no reconocido: '{valor}' (agrégalo a HOMOLOGACION_PRODUCTOS)", "ADVERTENCIA")
    return clave


def validar_merge(antes, despues, paso):
    """Detiene el proceso si un cruce cambia el número de filas de la base."""
    if len(antes) != len(despues):
        raise RuntimeError(f"El cruce '{paso}' cambió la base de {len(antes)} a {len(despues)} filas. "
                           "Revisa llaves duplicadas en la fuente.")
    log(f"Cruce '{paso}': {len(despues)} filas, sin duplicados")


# --------------------------------------------------------------------------- fuentes
def cargar_planta():
    df = limpiar_encabezados(pd.read_excel(C.CARPETA_FUENTES / "planta.xlsx"))
    df = df.rename(columns={
        buscar_columna(df, ["CODIGO", "COD"]): "CODIGO",
        buscar_columna(df, ["NOMBRE COMPLETO", "NOMBRE"]): "NOMBRE",
        buscar_columna(df, ["CARGO"]): "CARGO",
        buscar_columna(df, ["COD JEFE", "CODIGO JEFE"]): "CODIGO_JEFE",
        buscar_columna(df, ["ZONA", "ZONAL"]): "ZONA",
        buscar_columna(df, ["CORREO ELECTRONICO", "CORREO"]): "CORREO",
        buscar_columna(df, ["ESTADO"]): "ESTADO",
    })
    df["CODIGO"] = df.CODIGO.map(normalizar_codigo)
    df["CODIGO_JEFE"] = df.CODIGO_JEFE.map(normalizar_codigo)
    df["CARGO"] = df.CARGO.map(normalizar_texto)
    retirados = df[df.ESTADO.map(normalizar_texto) != "ACTIVO"]
    if len(retirados):
        log(f"{len(retirados)} personas retiradas excluidas de la planta", "ADVERTENCIA")
    df = df[df.ESTADO.map(normalizar_texto) == "ACTIVO"].copy()
    if df.CODIGO.duplicated().any():
        raise RuntimeError("Hay códigos duplicados en la planta.")
    # Cada comercial queda ligado a su zonal y, si aplica, a su gerente de centro de negocio
    zonales = df[df.CARGO == "GTE ZONAL"].set_index("ZONA")
    df["CODIGO_ZONAL"] = df.ZONA.map(zonales.CODIGO)
    df["NOMBRE_ZONAL"] = df.ZONA.map(zonales.NOMBRE)
    df["CODIGO_GERENTE_CN"] = np.where(df.CARGO.isin(["EJECUTIVO", "ASESOR"]), df.CODIGO_JEFE, "")
    log(f"Planta: {len(df)} personas activas en {df.ZONA.nunique() - 1} zonas")
    return df


def cargar_presupuesto():
    df = limpiar_encabezados(pd.read_excel(C.CARPETA_FUENTES / "presupuesto.xlsx"))
    cod = buscar_columna(df, ["COD. COMERCIAL", "CODIGO"])
    filas = []
    for corto, producto in (("PP", "PRESTAMO PERSONAL"), ("TC", "TARJETA DE CREDITO")):
        filas.append(pd.DataFrame({
            "CODIGO": df[cod].map(normalizar_codigo), "PRODUCTO": producto,
            "PPTO": pd.to_numeric(df[buscar_columna(df, [f"PPTO {corto} NOV"])], errors="coerce"),
            "PPTO_RADICACIONES": pd.to_numeric(df[buscar_columna(df, [f"PPTO RADIC {corto}"])], errors="coerce"),
        }))
    out = pd.concat(filas, ignore_index=True)
    log(f"Presupuesto: formato ancho convertido a {len(out)} filas código × producto")
    return out


def cargar_desembolsos():
    df = limpiar_encabezados(pd.read_csv(C.CARPETA_FUENTES / "desembolsos.csv", sep=";", encoding="utf-8-sig"))
    df["CODIGO"] = df[buscar_columna(df, ["COD COMERCIAL", "CODIGO"])].map(normalizar_codigo)
    df["PRODUCTO"] = df[buscar_columna(df, ["PRODUCTO"])].map(homologar_producto)
    df["FECHA"] = pd.to_datetime(df[buscar_columna(df, ["FECHA DESEMBOLSO", "FECHA"])], dayfirst=True, errors="coerce")
    df["VALOR"] = pd.to_numeric(df[buscar_columna(df, ["VALOR DESEMBOLSO", "VALOR"])], errors="coerce")
    fuera = df.FECHA.isna() | (df.FECHA.dt.date > C.FECHA_CORTE)
    if fuera.any():
        log(f"{int(fuera.sum())} operaciones sin fecha válida o posteriores al corte excluidas", "ADVERTENCIA")
    df = df[~fuera]
    # Préstamo: suma en millones. Tarjeta: número de tarjetas colocadas.
    pp = df[df.PRODUCTO == "PRESTAMO PERSONAL"].groupby("CODIGO").VALOR.sum().div(1e6).rename("REAL")
    tc = df[df.PRODUCTO == "TARJETA DE CREDITO"].groupby("CODIGO").size().rename("REAL").astype(float)
    out = pd.concat([pp.reset_index().assign(PRODUCTO="PRESTAMO PERSONAL"),
                     tc.reset_index().assign(PRODUCTO="TARJETA DE CREDITO")], ignore_index=True)
    log(f"Desembolsos: {len(df)} operaciones agregadas a {len(out)} filas")
    return out


def cargar_radicaciones():
    df = limpiar_encabezados(pd.read_csv(C.CARPETA_FUENTES / "radicaciones.csv"))
    df["CODIGO"] = df[buscar_columna(df, ["CODIGO"])].map(normalizar_codigo)
    df["PRODUCTO"] = df[buscar_columna(df, ["PRODUCTO"])].map(homologar_producto)
    out = df.groupby(["CODIGO", "PRODUCTO"]).size().rename("REAL_RADICACIONES").reset_index()
    log(f"Radicaciones: {len(df)} solicitudes")
    return out


def cargar_visitas():
    df = limpiar_encabezados(pd.read_excel(C.CARPETA_FUENTES / "visitas.xlsx"))
    out = pd.DataFrame({"CODIGO": df[buscar_columna(df, ["CODIGO"])].map(normalizar_codigo),
                        "REAL_VISITAS": pd.to_numeric(df[buscar_columna(df, ["VISITAS REALIZADAS", "VISITAS"])], errors="coerce")})
    return out.groupby("CODIGO", as_index=False).REAL_VISITAS.sum()


def cargar_tubo():
    df = limpiar_encabezados(pd.read_excel(C.CARPETA_FUENTES / "tubo_oportunidades.xlsx"))
    df["CODIGO"] = df.CODIGO.map(normalizar_codigo)
    df["PRODUCTO"] = df.PRODUCTO.map(homologar_producto)
    out = df.pivot_table(index=["CODIGO", "PRODUCTO"], columns="PLAZO CIERRE DIAS", values="VALOR", aggfunc="sum").reset_index()
    out.columns = ["CODIGO", "PRODUCTO"] + [f"TUBO_{int(c)}" for c in out.columns[2:]]
    return out


def cargar_historico():
    df = limpiar_encabezados(pd.read_excel(C.CARPETA_FUENTES / "historico.xlsx"))
    df["CODIGO"] = df.CODIGO.map(normalizar_codigo)
    df["PRODUCTO"] = df.PRODUCTO.map(homologar_producto)
    return df[["CODIGO", "PRODUCTO", "MES", "PPTO", "REAL"]]


# --------------------------------------------------------------------------- consolidación
def dias_habiles():
    habiles = [d.date() for d in pd.bdate_range(C.FECHA_CORTE.replace(day=1), pd.Timestamp(C.FECHA_CORTE) + pd.offsets.MonthEnd(0))
               if d.date() not in C.FESTIVOS]
    transcurridos = sum(d <= C.FECHA_CORTE for d in habiles)
    return {"dias_mes": len(habiles), "dias_transcurridos": transcurridos,
            "dias_restantes": len(habiles) - transcurridos, "avance": transcurridos / len(habiles)}


def construir_base():
    personas = cargar_planta()
    comerciales = personas[personas.CARGO.isin(["GTE RELACION", "GTE CN", "EJECUTIVO", "ASESOR"])]
    base = comerciales.merge(pd.DataFrame({"PRODUCTO": list(C.PRODUCTOS)}), how="cross")
    log(f"Base inicial: {len(comerciales)} comerciales × {len(C.PRODUCTOS)} productos = {len(base)} filas")

    for nombre, fuente, llaves in (("presupuesto", cargar_presupuesto(), ["CODIGO", "PRODUCTO"]),
                                   ("desembolsos", cargar_desembolsos(), ["CODIGO", "PRODUCTO"]),
                                   ("radicaciones", cargar_radicaciones(), ["CODIGO", "PRODUCTO"]),
                                   ("tubo", cargar_tubo(), ["CODIGO", "PRODUCTO"])):
        sin_planta = set(fuente.CODIGO) - set(personas.CODIGO)
        if sin_planta:
            log(f"{nombre}: {len(sin_planta)} códigos sin planta activa (se excluyen)", "ADVERTENCIA")
        antes = base
        base = base.merge(fuente, on=llaves, how="left")
        validar_merge(antes, base, nombre)

    # Las visitas son por persona, no por producto: se cruzan una sola vez
    antes = base
    base = base.merge(cargar_visitas(), on="CODIGO", how="left")
    validar_merge(antes, base, "visitas")
    base["PPTO_VISITAS"] = base.CARGO.map(C.PPTO_VISITAS_POR_ROL).astype(float)

    for col in ["REAL", "REAL_RADICACIONES", "REAL_VISITAS", "TUBO_30", "TUBO_60", "TUBO_90"]:
        base[col] = base[col].fillna(0.0)
    sin_ppto = base.PPTO.isna().sum()
    if sin_ppto:
        log(f"{sin_ppto} filas sin presupuesto: quedan nulas, no se inventan", "ADVERTENCIA")
    return personas, base


def main():
    C.CARPETA_DATOS.mkdir(exist_ok=True)
    personas, base = construir_base()
    historico = cargar_historico()
    corte = dias_habiles()
    personas.to_csv(C.CARPETA_DATOS / "personas.csv", index=False)
    base.to_csv(C.CARPETA_DATOS / "base_maestra.csv", index=False)
    historico.to_csv(C.CARPETA_DATOS / "historico_limpio.csv", index=False)
    calidad = {"fecha_corte": C.FECHA_CORTE.isoformat(), **corte, "filas_base": len(base),
               "comerciales": int(base.CODIGO.nunique()), "advertencias": ADVERTENCIAS}
    (C.CARPETA_DATOS / "calidad.json").write_text(json.dumps(calidad, ensure_ascii=False, indent=2), encoding="utf-8")
    log(f"Corte {C.FECHA_CORTE}: día hábil {corte['dias_transcurridos']} de {corte['dias_mes']}")


if __name__ == "__main__":
    main()
