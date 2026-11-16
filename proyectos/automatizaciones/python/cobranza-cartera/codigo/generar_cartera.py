"""Genera una cartera de clientes FICTICIA de «Estudio Ceiba» con corte al 15 de noviembre de 2026."""
import random
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

DATOS = Path(__file__).resolve().parents[1] / "datos"
CLIENTES = [
    ("Comercializadora Yarumo S.A.S.", "Marcela Ospina"), ("Clínica Dental Sonrisa", "Jorge Salazar"),
    ("Ferretería La Ceiba", "Patricia Lozano"), ("Hotel Mirador del Río", "Ricardo Muñoz"),
    ("Panadería Trigo Dorado", "Luz Dary Cárdenas"), ("Colegio Los Guaduales", "Hernán Quintero"),
    ("Distribuidora Ciruelo", "Natalia Arango"), ("Taller Automotriz El Piñón", "Óscar Benítez"),
    ("Óptica Visión Clara", "Carolina Rengifo"), ("Gimnasio Fuerza Andina", "Sebastián Mora"),
    ("Restaurante Sazón del Valle", "Gloria Patiño"), ("Agencia de Viajes Brisa", "Andrea Velasco"),
    ("Laboratorio Dental Nácar", "Mauricio Cifuentes"), ("Floristería Orquídea", "Beatriz Giraldo"),
]


def correo(contacto, empresa):
    usuario = ".".join(contacto.lower().split()[:2])
    for a, b in zip("áéíóúñ", "aeioun"):
        usuario = usuario.replace(a, b)
    dominio = "".join(w for w in empresa.lower().split()[:2] if w.isalpha())
    for a, b in zip("áéíóúñ", "aeioun"):
        dominio = dominio.replace(a, b)
    return f"{usuario}@{dominio}.ejemplo.test"


def main():
    rnd = random.Random(1115)
    corte = date(2026, 11, 15)
    filas, n = [], 2300
    for i, (empresa, contacto) in enumerate(CLIENTES):
        # Cada cliente tiene un comportamiento de pago distinto
        perfil = [0, 0, 0, 10, 20, 35, 50, 75, 110][i % 9]
        for _ in range(rnd.randint(1, 4)):
            n += rnd.randint(1, 5)
            atraso = max(-25, perfil + rnd.randint(-20, 20))
            vence = corte - timedelta(days=atraso)
            emision = vence - timedelta(days=30)
            valor = rnd.randrange(650_000, 6_500_000, 10_000)
            abono = valor * rnd.choice([0, 0, 0, 0.3, 0.5]) if atraso > 0 else 0
            filas.append([empresa, contacto, correo(contacto, empresa), f"FE-{n}", emision, vence, valor, round(abono)])
    df = pd.DataFrame(filas, columns=["cliente", "contacto", "correo", "factura", "fecha_emision", "fecha_vencimiento",
                                      "valor", "abonos"])
    df["fecha_emision"] = pd.to_datetime(df.fecha_emision)
    df["fecha_vencimiento"] = pd.to_datetime(df.fecha_vencimiento)
    DATOS.mkdir(exist_ok=True)
    df.to_excel(DATOS / "cartera_estudio_ceiba.xlsx", index=False, sheet_name="Cartera")
    print(f"[OK] {len(df)} facturas de {df.cliente.nunique()} clientes → {DATOS}")


if __name__ == "__main__":
    main()
