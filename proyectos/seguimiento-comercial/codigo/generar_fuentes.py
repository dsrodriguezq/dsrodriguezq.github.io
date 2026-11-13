"""
Paso 0 · Genera las fuentes FICTICIAS del sistema, tal como llegarían en la vida real:
en archivos separados, con encabezados inconsistentes, códigos con ".0", tildes,
productos escritos de varias formas y valores en pesos en lugar de millones.

Ningún dato proviene de una entidad real.

Archivos que crea en fuentes/:
    planta.xlsx              estructura comercial (jerarquía, cargos, correos)
    presupuesto.xlsx         metas de noviembre en formato ancho
    desembolsos.csv          operaciones del 3 al 13 de noviembre (una fila por operación)
    radicaciones.csv         solicitudes radicadas en noviembre
    visitas.xlsx             visitas comerciales del mes
    tubo_oportunidades.xlsx  negocios en curso por plazo de cierre
    historico.xlsx           real y presupuesto mensual de enero a octubre
    campanas.xlsx            clientes asignados en campañas comerciales y su gestión
"""
import numpy as np
import pandas as pd

import config as C

SEMILLA = 1113
rng = np.random.default_rng(SEMILLA)

NOMBRES = ["Andrés", "Camila", "Juliana", "Santiago", "Valentina", "Sebastián", "Daniela", "Felipe",
           "Laura", "Mateo", "Natalia", "Alejandro", "Carolina", "Juan Pablo", "Mariana", "David", "Paula",
           "Nicolás", "Sara", "Diego", "Manuela", "Esteban", "Catalina", "Julián", "Isabella", "Camilo",
           "Lina", "Tomás", "Angélica", "Simón", "Verónica", "Ricardo", "Adriana", "Mauricio", "Gloria"]
APELLIDOS = ["Gómez", "Rodríguez", "Martínez", "López", "García", "Hernández", "Ramírez", "Torres",
             "Castro", "Vargas", "Moreno", "Rojas", "Ortiz", "Jiménez", "Muñoz", "Restrepo", "Ospina",
             "Cardona", "Quintero", "Mejía", "Salazar", "Bermúdez", "Arango", "Zapata", "Pineda", "Duarte"]
ZONAS = ["Bogotá Norte", "Bogotá Centro", "Bogotá Sur", "Medellín", "Cali", "Barranquilla", "Cartagena",
         "Bucaramanga", "Pereira", "Manizales", "Ibagué", "Neiva", "Villavicencio", "Pasto", "Cúcuta",
         "Santa Marta", "Montería"]

_usados = set()


def persona():
    while True:
        nombre, apellido = rng.choice(NOMBRES), rng.choice(APELLIDOS)
        completo = f"{nombre} {apellido}"
        if completo not in _usados:
            _usados.add(completo)
            usuario = (nombre.split()[0] + "." + apellido).lower()
            for a, b in zip("áéíóúñ", "aeioun"):
                usuario = usuario.replace(a, b)
            return completo, f"{usuario}@{C.DOMINIO_CORREO}"


def dias_habiles(inicio, fin):
    dias = pd.bdate_range(inicio, fin)
    return [d for d in dias if d.date() not in C.FESTIVOS]


def generar_planta():
    filas, codigo = [], 40000
    nombre_div, correo_div = persona()
    filas.append(dict(codigo=39999, nombre=nombre_div, cargo="GTE DIVISIONAL", jefe=None, zona="DIVISIÓN",
                      correo=correo_div, estado="ACTIVO"))
    for zona in ZONAS:
        codigo += 1
        cod_zonal = codigo
        n, c = persona()
        filas.append(dict(codigo=cod_zonal, nombre=n, cargo="GTE ZONAL", jefe=39999, zona=zona, correo=c, estado="ACTIVO"))
        for _ in range(int(rng.integers(1, 3))):          # gerentes de relación (sin equipo)
            codigo += 1
            n, c = persona()
            filas.append(dict(codigo=codigo, nombre=n, cargo="GTE RELACION", jefe=cod_zonal, zona=zona, correo=c, estado="ACTIVO"))
        for _ in range(int(rng.integers(1, 3))):          # gerentes de centro de negocio (con equipo)
            codigo += 1
            cod_cn = codigo
            n, c = persona()
            filas.append(dict(codigo=cod_cn, nombre=n, cargo="GTE CN", jefe=cod_zonal, zona=zona, correo=c, estado="ACTIVO"))
            for cargo, k in (("EJECUTIVO", int(rng.integers(2, 4))), ("ASESOR", int(rng.integers(3, 7)))):
                for _ in range(k):
                    codigo += 1
                    n, c = persona()
                    estado = "RETIRADO" if rng.random() < 0.03 else "ACTIVO"
                    filas.append(dict(codigo=codigo, nombre=n, cargo=cargo, jefe=cod_cn, zona=zona, correo=c, estado=estado))
    return pd.DataFrame(filas)


def rasgos(planta):
    """Desempeño latente de cada comercial: nivel y qué tan estable es."""
    comerciales = planta[~planta.cargo.isin(["GTE DIVISIONAL", "GTE ZONAL"])].copy()
    clima = {z: rng.normal(0, 0.05) for z in ZONAS}
    comerciales["nivel"] = [float(np.clip(rng.normal(0.92 + clima[z], 0.15), 0.45, 1.5)) for z in comerciales.zona]
    comerciales["volatilidad"] = rng.uniform(0.05, 0.25, len(comerciales))
    factor = {z: rng.uniform(0.75, 1.3) for z in ZONAS}          # tamaño del mercado de cada zona
    comerciales["factor_zona"] = comerciales.zona.map(factor)
    return comerciales


PPTO_BASE = {   # meta mensual por rol: préstamo en millones, tarjeta en unidades
    "PRESTAMO PERSONAL": {"GTE RELACION": 900, "GTE CN": 600, "EJECUTIVO": 420, "ASESOR": 170},
    "TARJETA DE CREDITO": {"GTE RELACION": 22, "GTE CN": 18, "EJECUTIVO": 28, "ASESOR": 40},
}
TICKET_MM = 32   # monto promedio de un préstamo, en millones
CAMPANAS = {
    "PP": ["Preaprobados de fin de año", "Compra de cartera", "Retanqueo clientes actuales"],
    "TC": ["Tarjeta sin cuota de manejo", "Mejora a tarjeta Platinum"],
}


def generar_todo():
    C.CARPETA_FUENTES.mkdir(exist_ok=True)
    planta = generar_planta()
    com = rasgos(planta)
    habiles = dias_habiles("2026-11-01", "2026-11-30")
    transcurridos = [d for d in habiles if d.date() <= C.FECHA_CORTE]
    avance = len(transcurridos) / len(habiles)

    ppto_rows, desem, radic, visitas, tubo, hist, camp = [], [], [], [], [], [], []
    for r in com.itertuples():
        ppto_vis = C.PPTO_VISITAS_POR_ROL[r.cargo]
        fila_ppto = {"Cod. Comercial": f"{r.codigo}.0", "Nombre": r.nombre}
        momento = float(np.clip(r.nivel + rng.normal(0, r.volatilidad), 0.2, 1.8))   # cómo le va este mes
        for prod, base in PPTO_BASE.items():
            ppto = round(base[r.cargo] * r.factor_zona / (10 if prod.startswith("PRE") else 1)) * (10 if prod.startswith("PRE") else 1)
            ppto_rad = round(ppto / TICKET_MM * 1.7) if prod.startswith("PRE") else round(ppto * 1.5)
            corto = "PP" if prod.startswith("PRE") else "TC"
            fila_ppto[f"PPTO {corto} NOV"] = ppto
            fila_ppto[f"PPTO RADIC {corto}"] = ppto_rad

            # Desembolsos del mes a la fecha, en operaciones individuales
            objetivo = ppto * momento * avance * rng.normal(1, 0.08)
            variante = rng.choice(["Préstamo Personal", "PRESTAMO PERSONAL", "Libre Inversión", "Prest personal"]) if corto == "PP" \
                else rng.choice(["Tarjeta de Crédito", "TC", "T. CREDITO", "tarjeta"])
            if corto == "PP":
                acumulado = 0.0
                while acumulado < objetivo:
                    monto = float(np.clip(rng.lognormal(np.log(TICKET_MM), 0.45), 3, 180))
                    acumulado += monto
                    desem.append({"COD_COMERCIAL": r.codigo, "FECHA_DESEMBOLSO": rng.choice(transcurridos).strftime("%d/%m/%Y"),
                                  "PRODUCTO ": variante, "VALOR_DESEMBOLSO": round(monto * 1_000_000)})
                n_rad = int(rng.poisson(max(acumulado / TICKET_MM * 1.5, 0.1)))
            else:
                n_tc = int(rng.poisson(max(objetivo, 0.1)))
                for _ in range(n_tc):
                    desem.append({"COD_COMERCIAL": r.codigo, "FECHA_DESEMBOLSO": rng.choice(transcurridos).strftime("%d/%m/%Y"),
                                  "PRODUCTO ": variante, "VALOR_DESEMBOLSO": int(rng.choice([2, 3, 5, 8, 12]) * 1_000_000)})
                n_rad = int(rng.poisson(max(n_tc * 1.4, 0.1)))
            for _ in range(n_rad):
                radic.append({"codigo": f"{r.codigo}", "fecha_radicacion": rng.choice(transcurridos).strftime("%Y-%m-%d"),
                              "producto": variante.upper(), "estado": rng.choice(["APROBADA", "EN ESTUDIO", "NEGADA"], p=[.6, .3, .1])})

            # Tubo de oportunidades: negocios en curso por plazo esperado de cierre
            for plazo in (30, 60, 90):
                peso = {30: 0.55, 60: 0.35, 90: 0.25}[plazo]
                tubo.append({"CODIGO": r.codigo, "PRODUCTO": prod.title(), "PLAZO_CIERRE_DIAS": plazo,
                             "VALOR": round(max(ppto * peso * rng.normal(r.nivel, 0.25), 0), 1)})

            # Campañas: clientes asignados, cuántos ya se gestionaron y cuántos compraron
            for nombre_camp in CAMPANAS[corto]:
                if r.cargo == "GTE RELACION" and rng.random() < 0.5:
                    continue
                asignados = int(rng.integers(4, 18))
                gestion = float(np.clip(rng.normal(0.45 * avance / 0.47 * (0.7 + 0.3 * r.nivel), 0.15), 0.02, 1))
                gestionados = int(round(asignados * gestion))
                convertidos = int(rng.binomial(gestionados, float(np.clip(rng.normal(0.22, 0.06), 0.03, 0.5))))
                ticket = TICKET_MM * rng.uniform(0.7, 1.3) if corto == "PP" else 1
                camp.append({"Codigo Asesor": r.codigo, "Campaña": nombre_camp, "Producto": prod.title(),
                             "Clientes asignados": asignados, "Clientes gestionados": gestionados,
                             "Clientes convertidos": convertidos, "Potencial": round(asignados * ticket, 1)})

            # Histórico enero-octubre: cumplimiento alrededor del nivel del comercial
            for mes in range(1, 11):
                if rng.random() < 0.08:      # meses sin dato (ingresó tarde o no tuvo meta)
                    continue
                cump = float(np.clip(rng.normal(r.nivel, r.volatilidad), 0, 2.2))
                hist.append({"CODIGO": r.codigo, "PRODUCTO": prod, "MES": f"2026-{mes:02d}",
                             "PPTO": ppto, "REAL": round(ppto * cump, 1)})

        ppto_rows.append(fila_ppto)
        vis_real = max(0, int(rng.normal(ppto_vis * avance * (0.75 + 0.3 * r.nivel), 2.5))) if ppto_vis else int(rng.integers(0, 3))
        visitas.append({"CODIGO ": f"{r.codigo}.0", "VISITAS REALIZADAS": vis_real})

    # Exporta con nombres y formatos deliberadamente distintos entre archivos
    planta.rename(columns={"codigo": "CÓDIGO", "nombre": "NOMBRE COMPLETO", "cargo": "CARGO", "jefe": "COD JEFE",
                           "zona": "ZONA", "correo": "CORREO ELECTRÓNICO", "estado": "ESTADO"}) \
        .to_excel(C.CARPETA_FUENTES / "planta.xlsx", index=False, sheet_name="PLANTA")
    pd.DataFrame(ppto_rows).to_excel(C.CARPETA_FUENTES / "presupuesto.xlsx", index=False, sheet_name="NOV 2026")
    pd.DataFrame(desem).to_csv(C.CARPETA_FUENTES / "desembolsos.csv", index=False, sep=";", encoding="utf-8-sig")
    pd.DataFrame(radic).to_csv(C.CARPETA_FUENTES / "radicaciones.csv", index=False, encoding="utf-8")
    pd.DataFrame(visitas).to_excel(C.CARPETA_FUENTES / "visitas.xlsx", index=False)
    pd.DataFrame(tubo).to_excel(C.CARPETA_FUENTES / "tubo_oportunidades.xlsx", index=False)
    pd.DataFrame(hist).to_excel(C.CARPETA_FUENTES / "historico.xlsx", index=False)
    pd.DataFrame(camp).to_excel(C.CARPETA_FUENTES / "campanas.xlsx", index=False, sheet_name="CAMPAÑAS")
    print(f"Planta: {len(planta)} personas | Desembolsos: {len(desem)} operaciones | "
          f"Radicaciones: {len(radic)} | Histórico: {len(hist)} filas | Avance del mes: {avance:.0%}")


if __name__ == "__main__":
    generar_todo()
