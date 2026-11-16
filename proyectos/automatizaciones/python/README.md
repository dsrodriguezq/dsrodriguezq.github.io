# Automatizaciones en Python

Cuatro procesos que en muchas pymes se hacen a mano cada semana o cada mes. Cada uno trae su generador de datos de prueba, el script que hace el trabajo y un reporte HTML que se publica en el portafolio.

| Proyecto | Qué automatiza | Datos | Reporte |
|---|---|---|---|
| [`facturas-dian/`](facturas-dian/) | Lee facturas electrónicas XML (UBL 2.1), las consolida en Excel y detecta errores antes de pagar | 100 % ficticios | [Ver](https://dsrodriguezq.github.io/proyectos/automatizaciones/python/facturas-dian/salida/reporte.html) |
| [`conciliacion-bancaria/`](conciliacion-bancaria/) | Cruza el extracto del banco contra el auxiliar contable y arma la prueba de saldos | 100 % ficticios | [Ver](https://dsrodriguezq.github.io/proyectos/automatizaciones/python/conciliacion-bancaria/salida/reporte.html) |
| [`cobranza-cartera/`](cobranza-cartera/) | Edades de cartera, priorización y correos de cobro con el tono de cada tramo | 100 % ficticios | [Ver](https://dsrodriguezq.github.io/proyectos/automatizaciones/python/cobranza-cartera/salida/reporte.html) |
| [`monitor-trm/`](monitor-trm/) | Descarga la TRM oficial cada día hábil, guarda el histórico y abre una alerta si se mueve fuerte | Públicos reales | [Ver](https://dsrodriguezq.github.io/proyectos/automatizaciones/python/monitor-trm/salida/reporte.html) |

`comun/reporte.py` reúne el estilo compartido de los reportes.

## Correrlos

Requiere Python 3.11 o superior con `pandas` y `openpyxl`.

```bash
pip install pandas openpyxl

# Facturas
python facturas-dian/codigo/generar_facturas.py
python facturas-dian/codigo/leer_facturas.py            # o pasa tu propia carpeta de XML

# Conciliación
python conciliacion-bancaria/codigo/generar_datos.py
python conciliacion-bancaria/codigo/conciliar.py

# Cobranza (no envía correos: ENVIAR = False)
python cobranza-cartera/codigo/generar_cartera.py
python cobranza-cartera/codigo/cobranza.py

# TRM (descarga datos reales de datos.gov.co)
python monitor-trm/codigo/trm.py
```

## Detalle de cada uno

**Facturas electrónicas.** Valida el dígito de verificación del NIT con el algoritmo de la DIAN, revisa que el IVA del encabezado sea igual a la suma de las líneas, que el total sea base + IVA, y detecta duplicados por NIT + número o por CUFE. Las 13 facturas de prueba traen 4 errores sembrados y el lector encuentra los 4. *Nota: los XML reales de la DIAN llegan dentro de un `AttachedDocument`; aquí se usa la factura UBL directa para simplificar.*

**Conciliación bancaria.** Aplica tres reglas en orden: exacta (valor y fecha), fecha cercana (mismo valor, hasta 3 días) y referencia con valor distinto. Clasifica lo pendiente en cheques y consignaciones en tránsito y notas débito o crédito por registrar. Si la prueba de saldos no cuadra, el script termina con error.

**Cobranza de cartera.** Prioriza por saldo vencido ponderado según la gravedad del tramo y fija la fecha de seguimiento en días hábiles. El envío real se activa con `ENVIAR = True` y credenciales SMTP en variables de entorno, nunca en el código.

**Monitor de la TRM.** Usa la API Socrata de datos.gov.co (conjunto `32sa-8pi3`) con reintentos. GitHub Actions lo corre de lunes a sábado (`.github/workflows/monitor-trm.yml`) y, si la variación diaria supera 1,5 %, abre un *issue* en GitHub, que llega por correo.
