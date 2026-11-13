"""Parámetros del Sistema de Seguimiento Comercial (banco ficticio "Banco Andino").

Todos los valores son inventados para este proyecto de demostración.
"""
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
CARPETA_FUENTES = RAIZ / "fuentes"
CARPETA_DATOS = RAIZ / "datos"
CARPETA_CORREOS = RAIZ / "correos"

BANCO = "Banco Andino (ficticio)"
DOMINIO_CORREO = "bancoandino.example"   # dominio reservado: nunca recibe correos reales

# Corte del seguimiento: mitad de noviembre de 2026
FECHA_CORTE = date(2026, 11, 13)
FESTIVOS = [date(2026, 11, 2), date(2026, 11, 16)]   # festivos de noviembre en Colombia

# Productos: el préstamo se mide en millones de pesos; la tarjeta, en unidades
PRODUCTOS = {
    "PRESTAMO PERSONAL": {"etiqueta": "Préstamo Personal", "monetario": True},
    "TARJETA DE CREDITO": {"etiqueta": "Tarjeta de Crédito", "monetario": False},
}

# Variantes con las que llega el nombre del producto en las fuentes
HOMOLOGACION_PRODUCTOS = {
    "PRESTAMO PERSONAL": "PRESTAMO PERSONAL", "PRESTAMO": "PRESTAMO PERSONAL",
    "PREST PERSONAL": "PRESTAMO PERSONAL", "LIBRE INVERSION": "PRESTAMO PERSONAL",
    "TARJETA DE CREDITO": "TARJETA DE CREDITO", "TC": "TARJETA DE CREDITO",
    "TARJETA": "TARJETA DE CREDITO", "T. CREDITO": "TARJETA DE CREDITO",
}

# Meta de visitas al mes por rol
PPTO_VISITAS_POR_ROL = {"GTE RELACION": 20, "GTE CN": 12, "EJECUTIVO": 18, "ASESOR": 0}

# Pronóstico: peso del ritmo del mes frente al histórico del comercial
PESO_RITMO = 0.6
PESO_HISTORICO = 0.4
VOLATILIDAD_MINIMA = 0.05
MESES_MINIMOS_PROBABILIDAD = 3
UMBRAL_ALTA = 0.70
UMBRAL_RIESGO = 0.40

# Correos
MODO_PRUEBA = False                 # True: una muestra por nivel, todo al correo de prueba
CORREO_PRUEBA = f"pruebas@{DOMINIO_CORREO}"
ENVIAR = False                      # False: solo genera vistas previas (.html y .eml)
TOP_N = 3
