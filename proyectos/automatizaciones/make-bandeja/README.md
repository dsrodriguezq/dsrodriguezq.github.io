# Bandeja inteligente de solicitudes · Make

> **Datos 100 % ficticios.** «Estudio Ceiba» es un negocio inventado y los correos usan el dominio reservado `ejemplo.test`.

## El problema

Un estudio contable recibe cotizaciones, preguntas de soporte y quejas por el mismo formulario. Alguien las lee una por una, las copia a una hoja y decide a quién avisar. Las quejas urgentes se pierden entre las demás.

## La solución

Un escenario de Make (plan gratuito) que recibe cada solicitud, limpia los datos, la clasifica con reglas y la deja en la pestaña correcta de Google Sheets. Además avisa por correo cuando es una queja.

```
Webhook ─► Limpieza (lower, trim, fecha) ─► Router
                                             ├─ Quejas:        tipo = queja  O  mensaje contiene «reclamo» ─► Sheets «Quejas» ─► Gmail urgente
                                             ├─ Cotizaciones:  tipo = cotizacion  Y  no contiene «reclamo» ─► Sheets «Cotizaciones» ─► Gmail de acuse
                                             ├─ Soporte:       tipo = soporte  Y  no contiene «reclamo»    ─► Sheets «Soporte»
                                             └─ Otros (ruta por defecto)                                  ─► Sheets «Otros»
Manejador de errores ─► Sheets «Errores»
```

**Importante:** el router de Make ejecuta *todas* las rutas cuyo filtro se cumpla. Por eso los filtros son excluyentes: una solicitud de soporte que dice «reclamo» va solo a Quejas.

## Especificación

| Elemento | Detalle |
|---|---|
| Disparador | Webhooks › Custom webhook. Campos: `nombre, correo, tipo, mensaje, monto` |
| Limpieza | `tipo_limpio = lower(trim(tipo))`, `recibido = formatDate(now; "YYYY-MM-DD HH:mm")` |
| Hoja | `Bandeja Estudio Ceiba` con pestañas Cotizaciones, Soporte, Quejas, Otros y Errores. Columnas: `recibido, nombre, correo, tipo, mensaje, monto, ruta` |
| Correos | Solo a tu propio correo durante la demo |
| Plan | Gratuito: 1 escenario activo de los 2 permitidos. Cada módulo ejecutado consume un crédito (≈5 por solicitud) |

## Prueba

`datos_prueba.csv` trae 9 solicitudes con errores a propósito: mayúsculas y espacios en `tipo`, y un «reclamo» escrito como soporte. Resultado esperado:

| Ruta | Solicitudes |
|---|---|
| Cotizaciones | Laura, Julián, Valentina |
| Soporte | Andrés, Sofía |
| Quejas | Camila, Felipe, Daniela |
| Otros | Mateo |

## Archivos

- `datos_prueba.csv`: las 9 solicitudes de prueba.
- `blueprint.json`: el escenario exportado desde Make, sin credenciales ni la URL del webhook. *(Se agrega al terminar.)*
