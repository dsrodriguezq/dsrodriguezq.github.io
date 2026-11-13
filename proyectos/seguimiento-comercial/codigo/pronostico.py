"""
Paso 2 · Indicadores, pronóstico de cierre, probabilidad de cumplir y segmentación.

Construye cuatro niveles a partir de la base maestra:
    DIVISIONAL   toda la fuerza comercial
    ZONALES      una fila por zona y producto
    UNIDADES     cada gerente con su equipo (gerente de centro de negocio + ejecutivos + asesores)
                 o solo (gerente de relación)
    COMERCIALES  cada persona

Pronóstico de cierre de mes:
    ritmo      = real a la fecha / avance de días hábiles
    histórico  = presupuesto × cumplimiento mediano de enero a octubre
    pronóstico = 60 % ritmo + 40 % histórico (nunca menor a lo ya colocado)
Probabilidad de cumplir = Φ((cumplimiento pronosticado − 1) / volatilidad histórica),
calculada solo con 3 o más meses de historia.

Segmentación: K-Means (k = 3) sobre cumplimiento al corte, probabilidad y avance de
radicaciones, por producto.

Salidas en datos/:
    consolidado.json             lo que leen el tablero y los correos
    Tablero_Consolidado.xlsx     las mismas tablas para Excel
"""
import json
import math

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler

import config as C

METRICAS = ["PPTO", "REAL", "PPTO_RADICACIONES", "REAL_RADICACIONES", "TUBO_30", "TUBO_60", "TUBO_90",
            "CAMP_ASIGNADOS", "CAMP_GESTIONADOS", "CAMP_CONVERTIDOS", "CAMP_POTENCIAL"]
SEGMENTOS = ["Prioridad de acompañamiento", "En observación", "Sólidos"]


def cargar():
    calidad = json.loads((C.CARPETA_DATOS / "calidad.json").read_text(encoding="utf-8"))
    base = pd.read_csv(C.CARPETA_DATOS / "base_maestra.csv", dtype={"CODIGO": str, "CODIGO_JEFE": str,
                                                                    "CODIGO_ZONAL": str, "CODIGO_GERENTE_CN": str})
    hist = pd.read_csv(C.CARPETA_DATOS / "historico_limpio.csv", dtype={"CODIGO": str})
    personas = pd.read_csv(C.CARPETA_DATOS / "personas.csv", dtype={"CODIGO": str, "CODIGO_JEFE": str})
    return calidad, base, hist, personas


def estadisticas_historicas(hist, miembros):
    """Mediana, volatilidad y meses válidos del cumplimiento mensual de un grupo de códigos."""
    h = hist[hist.CODIGO.isin(miembros)].groupby("MES")[["REAL", "PPTO"]].sum()
    cump = (h.REAL / h.PPTO.replace(0, np.nan)).dropna()
    return {"mediana": float(cump.median()) if len(cump) else np.nan,
            "volatilidad": float(cump.std(ddof=1)) if len(cump) > 1 else np.nan,
            "meses": int(len(cump))}


def pronosticar(fila, avance):
    ppto, real = fila["PPTO"], fila["REAL"]
    ritmo = real / avance if avance > 0 else np.nan
    historico = ppto * float(np.clip(fila["HIST_MEDIANA"], 0.25, 1.75)) if ppto > 0 and fila["HIST_MEDIANA"] > 0 else np.nan
    if not np.isnan(ritmo) and not np.isnan(historico):
        pron = C.PESO_RITMO * ritmo + C.PESO_HISTORICO * historico
    else:
        pron = ritmo if not np.isnan(ritmo) else historico
    pron = max(pron, real)
    cump = pron / ppto if ppto > 0 else np.nan
    prob = np.nan
    if fila["HIST_MESES"] >= C.MESES_MINIMOS_PROBABILIDAD and not np.isnan(cump):
        sigma = max(fila["HIST_VOLATILIDAD"] if not np.isnan(fila["HIST_VOLATILIDAD"]) else 0, C.VOLATILIDAD_MINIMA)
        prob = 0.5 * (1 + math.erf(((cump - 1) / sigma) / math.sqrt(2)))
    if np.isnan(prob):
        alerta = "SIN HISTORIA"
    elif prob >= C.UMBRAL_ALTA:
        alerta = "ALTA PROBABILIDAD"
    elif prob >= C.UMBRAL_RIESGO:
        alerta = "EN RIESGO"
    else:
        alerta = "BAJA PROBABILIDAD"
    return pd.Series({"PRON_REAL": pron, "PRON_CUMP": cump, "PROB": prob, "ALERTA": alerta})


def indicadores(df, corte):
    av, restantes = corte["avance"], max(corte["dias_restantes"], 1)
    df = df.copy()
    df["PPTO_CORTE"] = df.PPTO * av
    df["CUMP_CORTE"] = df.REAL / df.PPTO_CORTE.replace(0, np.nan)
    df["CUMP_MES"] = df.REAL / df.PPTO.replace(0, np.nan)
    df["CUMP_RAD_CORTE"] = df.REAL_RADICACIONES / (df.PPTO_RADICACIONES * av).replace(0, np.nan)
    df["BRECHA"] = (df.PPTO - df.REAL).clip(lower=0)
    df["BRECHA_RAD"] = (df.PPTO_RADICACIONES - df.REAL_RADICACIONES).clip(lower=0)
    df["META_DIARIA"] = df.BRECHA / restantes
    return pd.concat([df, df.apply(pronosticar, axis=1, avance=av)], axis=1)


def agregar(base, llaves, hist, miembros_por_grupo):
    g = base.groupby(llaves, as_index=False)[METRICAS].sum()
    stats = [estadisticas_historicas(hist[hist.PRODUCTO == r.PRODUCTO], miembros_por_grupo(r)) for r in g.itertuples()]
    g["HIST_MEDIANA"] = [s["mediana"] for s in stats]
    g["HIST_VOLATILIDAD"] = [s["volatilidad"] for s in stats]
    g["HIST_MESES"] = [s["meses"] for s in stats]
    return g


def visitas_por_grupo(base, llave):
    """Las visitas son por persona: se suman una sola vez, sin repetirlas por producto."""
    p = base.drop_duplicates("CODIGO")
    return p.groupby(llave)[["REAL_VISITAS", "PPTO_VISITAS"]].sum()


def accion(r, corte, monetario):
    av = corte["avance"]
    fmt = (lambda v: f"${v:,.0f} M".replace(",", ".")) if monetario else (lambda v: f"{v:,.0f}".replace(",", "."))
    if r.CUMP_CORTE >= 1.1 and r.ALERTA == "ALTA PROBABILIDAD":
        return "Va adelante del ritmo: proponer una meta extendida y compartir su práctica con el equipo."
    if r.ALERTA == "ALTA PROBABILIDAD":
        return f"Mantener el ritmo: necesita {fmt(r.META_DIARIA)} por día hábil para cerrar el mes."
    rad_faltantes = r.PPTO_RADICACIONES * av - r.REAL_RADICACIONES
    if r.CUMP_RAD_CORTE < 0.8 and rad_faltantes >= 1:
        return f"Embudo débil: radicar {math.ceil(rad_faltantes)} solicitudes más esta semana para alimentar el cierre."
    if r.TUBO_30 >= r.BRECHA > 0:
        return f"El tubo a 30 días ({fmt(r.TUBO_30)}) cubre la brecha: priorizar el cierre de esas oportunidades."
    if getattr(r, "PPTO_VISITAS", 0) and r.REAL_VISITAS < r.PPTO_VISITAS * av * 0.8:
        return f"Agenda corta: hacer {math.ceil(r.PPTO_VISITAS * av - r.REAL_VISITAS)} visitas más antes del cierre."
    return f"Reunión 1:1 esta semana: necesita {fmt(r.META_DIARIA)} por día hábil y hoy no lleva el ritmo."


def segmentar(com):
    com = com.copy()
    com["SEGMENTO"] = ""
    for prod in C.PRODUCTOS:
        m = com.PRODUCTO == prod
        x = com.loc[m, ["CUMP_CORTE", "PROB", "CUMP_RAD_CORTE"]].copy()
        x = x.fillna(x.median())
        km = KMeans(n_clusters=3, n_init=20, random_state=7).fit(StandardScaler().fit_transform(x))
        orden = pd.Series(km.labels_, index=x.index).groupby(km.labels_).apply(lambda s: com.loc[s.index, "PROB"].fillna(0.5).mean())
        nombres = {grupo: SEGMENTOS[i] for i, grupo in enumerate(orden.sort_values().index)}
        com.loc[m, "SEGMENTO"] = [nombres[k] for k in km.labels_]
    return com


def redondear(df, columnas):
    out = df[columnas].copy()
    for c in out.columns:
        if pd.api.types.is_float_dtype(out[c]):
            out[c] = out[c].round(4)
    return json.loads(out.to_json(orient="records", force_ascii=False))


def main():
    corte, base, hist, personas = cargar()
    hist["CODIGO"] = hist.CODIGO.astype(str)
    equipos = base.groupby("CODIGO_GERENTE_CN").CODIGO.apply(set).to_dict()

    # COMERCIALES
    com = base.copy()
    stats = [estadisticas_historicas(hist[hist.PRODUCTO == r.PRODUCTO], {r.CODIGO}) for r in com.itertuples()]
    com["HIST_MEDIANA"] = [s["mediana"] for s in stats]
    com["HIST_VOLATILIDAD"] = [s["volatilidad"] for s in stats]
    com["HIST_MESES"] = [s["meses"] for s in stats]
    com = segmentar(indicadores(com, corte))
    com["ACCION"] = [accion(r, corte, C.PRODUCTOS[r.PRODUCTO]["monetario"]) for r in com.itertuples()]

    # UNIDADES: cada gerente con su equipo
    base_u = base.copy()
    base_u["CODIGO_UNIDAD"] = np.where(base_u.CODIGO_GERENTE_CN.fillna("") != "", base_u.CODIGO_GERENTE_CN, base_u.CODIGO)
    uni = agregar(base_u, ["CODIGO_UNIDAD", "PRODUCTO"], hist,
                  lambda r: {r.CODIGO_UNIDAD} | equipos.get(r.CODIGO_UNIDAD, set()))
    jefes = base.drop_duplicates("CODIGO").set_index("CODIGO")
    uni["NOMBRE"] = uni.CODIGO_UNIDAD.map(jefes.NOMBRE)
    uni["CARGO"] = uni.CODIGO_UNIDAD.map(jefes.CARGO)
    uni["ZONA"] = uni.CODIGO_UNIDAD.map(jefes.ZONA)
    uni["CORREO"] = uni.CODIGO_UNIDAD.map(jefes.CORREO)
    uni["PERSONAS"] = uni.CODIGO_UNIDAD.map(lambda c: 1 + len(equipos.get(c, set())))
    vis = visitas_por_grupo(base_u, "CODIGO_UNIDAD")
    uni = uni.join(vis, on="CODIGO_UNIDAD")
    uni = indicadores(uni, corte)
    uni["ACCION"] = [accion(r, corte, C.PRODUCTOS[r.PRODUCTO]["monetario"]) for r in uni.itertuples()]

    # ZONALES
    zon = agregar(base, ["ZONA", "PRODUCTO"], hist, lambda r: set(base.loc[base.ZONA == r.ZONA, "CODIGO"]))
    zonales = personas[personas.CARGO == "GTE ZONAL"].set_index("ZONA")
    zon["NOMBRE_ZONAL"] = zon.ZONA.map(zonales.NOMBRE)
    zon["CORREO"] = zon.ZONA.map(zonales.CORREO)
    zon = zon.join(visitas_por_grupo(base, "ZONA"), on="ZONA")
    zon = indicadores(zon, corte)

    # DIVISIONAL
    base_d = base.assign(DIVISION="TOTAL")
    div = agregar(base_d, ["DIVISION", "PRODUCTO"], hist, lambda r: set(base.CODIGO))
    div = div.join(visitas_por_grupo(base_d, "DIVISION"), on="DIVISION")
    div = indicadores(div, corte)
    divisional = personas[personas.CARGO == "GTE DIVISIONAL"].iloc[0]

    # Histórico divisional mensual para el gráfico de tendencia
    hd = hist.groupby(["PRODUCTO", "MES"], as_index=False)[["REAL", "PPTO"]].sum()
    hd["CUMP"] = hd.REAL / hd.PPTO

    comunes = ["PRODUCTO", "PPTO", "REAL", "PPTO_CORTE", "CUMP_CORTE", "CUMP_MES", "PPTO_RADICACIONES",
               "REAL_RADICACIONES", "CUMP_RAD_CORTE", "REAL_VISITAS", "PPTO_VISITAS", "BRECHA", "BRECHA_RAD",
               "META_DIARIA", "TUBO_30", "TUBO_60", "TUBO_90", "CAMP_ASIGNADOS", "CAMP_GESTIONADOS",
               "CAMP_CONVERTIDOS", "CAMP_POTENCIAL", "PRON_REAL", "PRON_CUMP", "PROB", "ALERTA", "HIST_MESES"]
    salida = {
        "meta": {"banco": C.BANCO, "corte": corte, "productos": C.PRODUCTOS,
                 "divisional": {"nombre": divisional.NOMBRE, "correo": divisional.CORREO},
                 "aviso": "Datos 100 % ficticios generados por código. No corresponden a ninguna entidad real."},
        "divisional": redondear(div, comunes),
        "zonales": redondear(zon, ["ZONA", "NOMBRE_ZONAL", "CORREO"] + comunes),
        "unidades": redondear(uni, ["CODIGO_UNIDAD", "NOMBRE", "CARGO", "ZONA", "CORREO", "PERSONAS", "ACCION"] + comunes),
        "comerciales": redondear(com, ["CODIGO", "NOMBRE", "CARGO", "ZONA", "CODIGO_GERENTE_CN", "SEGMENTO", "ACCION"] + comunes),
        "historico": redondear(hd, ["PRODUCTO", "MES", "REAL", "PPTO", "CUMP"]),
    }
    (C.CARPETA_DATOS / "consolidado.json").write_text(json.dumps(salida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    with pd.ExcelWriter(C.CARPETA_DATOS / "Tablero_Consolidado.xlsx") as xl:
        div.to_excel(xl, "DIVISIONAL", index=False)
        zon.to_excel(xl, "ZONALES", index=False)
        uni.to_excel(xl, "UNIDADES", index=False)
        com.to_excel(xl, "COMERCIALES", index=False)

    for prod in C.PRODUCTOS:
        d = div[div.PRODUCTO == prod].iloc[0]
        print(f"[OK] {prod}: cumplimiento al corte {d.CUMP_CORTE:.1%} | pronóstico {d.PRON_CUMP:.1%} | "
              f"probabilidad {d.PROB:.0%} | {d.ALERTA}")
    print(com.groupby(["PRODUCTO", "SEGMENTO"]).size().to_string())
    print(zon.groupby(["PRODUCTO", "ALERTA"]).size().to_string())


if __name__ == "__main__":
    main()
