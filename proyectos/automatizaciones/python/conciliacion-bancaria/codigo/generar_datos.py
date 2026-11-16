"""Genera un extracto bancario y un auxiliar contable FICTICIOS de octubre de 2026.

Para que la conciliación tenga trabajo de verdad, los datos traen:
- movimientos que el banco registra 1 a 3 días después que contabilidad;
- cheques en tránsito y una consignación del último día que el banco aún no refleja;
- cobros del banco que contabilidad no ha registrado (GMF 4x1000, comisiones, intereses);
- un error de digitación en el auxiliar (1.250.000 en vez de 1.205.000).
"""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATOS = Path(__file__).resolve().parents[1] / "datos"

CLIENTES = ["Comercializadora Yarumo", "Clínica Dental Sonrisa", "Ferretería La Ceiba", "Hotel Mirador del Río",
            "Panadería Trigo Dorado", "Colegio Los Guaduales"]
PROVEEDORES = ["Papelería El Samán", "Tecnored Andina", "Café de la Montaña", "Aseo Integral Pacífico",
               "Transportes Río Cauca", "Software Guadua"]


def main():
    rnd = random.Random(1031)
    DATOS.mkdir(exist_ok=True)
    libro, banco = [], []
    dia = date(2026, 10, 1)
    n_ref = 4100

    for i in range(38):
        fecha = dia + timedelta(days=rnd.randint(0, 27))
        ingreso = rnd.random() < 0.45
        n_ref += rnd.randint(1, 9)
        if ingreso:
            tercero = rnd.choice(CLIENTES)
            valor = rnd.randrange(800_000, 9_000_000, 1000)
            desc_l, desc_b = f"Recaudo FV-{n_ref} {tercero}", f"ABONO PSE {n_ref} {tercero.upper()[:18]}"
        else:
            tercero = rnd.choice(PROVEEDORES)
            valor = -rnd.randrange(150_000, 4_500_000, 1000)
            desc_l, desc_b = f"Pago factura {n_ref} {tercero}", f"PAGO PROVEEDOR REF {n_ref}"
        retraso = 0 if rnd.random() < 0.6 else rnd.randint(1, 3)
        libro.append([fecha, desc_l, str(n_ref), valor])
        banco.append([fecha + timedelta(days=retraso), desc_b, str(n_ref), valor])

    # Error de digitación: el banco pagó 1.205.000 y contabilidad registró 1.250.000
    n_ref += 3
    libro.append([date(2026, 10, 14), f"Pago factura {n_ref} Software Guadua", str(n_ref), -1_250_000])
    banco.append([date(2026, 10, 14), f"PAGO PROVEEDOR REF {n_ref}", str(n_ref), -1_205_000])

    # Partidas solo en libros (aún no llegan al banco)
    for k, (tercero, v) in enumerate([("Aseo Integral Pacífico", -840_000), ("Transportes Río Cauca", -1_120_000),
                                      ("Tecnored Andina", -2_300_000)]):
        libro.append([date(2026, 10, 29 + k % 3), f"Cheque {77210 + k} {tercero}", f"CH{77210 + k}", v])
    libro.append([date(2026, 10, 31), "Consignación efectivo ventas del día", "CONS-1031", 3_450_000])

    # Partidas solo en el banco (contabilidad no las ha registrado)
    egresos = -sum(v for *_, v in banco if v < 0)
    banco.append([date(2026, 10, 31), "GMF 4X1000 OCTUBRE", "", -round(egresos * 0.004)])
    banco.append([date(2026, 10, 31), "COMISION MANEJO CUENTA", "", -38_500])
    banco.append([date(2026, 10, 15), "COMISION TRANSFERENCIA ACH", "", -7_900])
    banco.append([date(2026, 10, 31), "ABONO INTERESES AHORRO", "", 21_340])

    cols = ["fecha", "descripcion", "referencia", "valor"]
    lb = pd.DataFrame(libro, columns=cols).sort_values("fecha", kind="stable")
    bc = pd.DataFrame(banco, columns=cols).sort_values("fecha", kind="stable")
    # El extracto real no trae la referencia en columna aparte: va dentro de la descripción
    bc = bc.drop(columns="referencia")
    bc["fecha"] = pd.to_datetime(bc.fecha).dt.strftime("%d/%m/%Y")
    lb["fecha"] = pd.to_datetime(lb.fecha)
    lb.to_excel(DATOS / "auxiliar_bancos_octubre.xlsx", index=False, sheet_name="Auxiliar 1110-05")
    bc.to_csv(DATOS / "extracto_banco_andino_octubre.csv", index=False, sep=";", decimal=",")
    print(f"[OK] auxiliar: {len(lb)} movimientos · extracto: {len(bc)} movimientos → {DATOS}")


if __name__ == "__main__":
    main()
