# Captura de prospectos con aviso inmediato · Zapier

> **Datos 100 % ficticios.** «Estudio Ceiba» es un negocio inventado.

## El problema

Los prospectos llenan un formulario y nadie lo revisa hasta el día siguiente. Para entonces ya contrataron a otro.

## La solución

Dos Zaps del plan gratuito, que solo permite un disparador y una acción por Zap, encadenados con Google Sheets como puente:

```
Zap 1:  Google Forms (nueva respuesta) ─► Google Sheets «CRM» (fila nueva, estado = Nuevo)
Zap 2:  Google Sheets «CRM» (fila nueva) ─► Gmail (aviso al equipo con prioridad en el asunto)
```

La hoja calcula la prioridad con una fórmula, así que no hace falta un paso de filtro, que es de pago. La fórmula va **solo en G1** y se extiende sola a cada fila nueva:

```
=ARRAYFORMULA(SI(FILA(F:F)=1;"prioridad";SI(F:F="";"";SI(F:F>=2000000;"Alta";"Normal"))))
```

En el Zap 1 deja vacía la columna `prioridad`. Si Zapier escribe algo ahí, la fórmula se rompe.

## Especificación

| Elemento | Detalle |
|---|---|
| Formulario | «Solicita tu asesoría – Estudio Ceiba». Campos: nombre, correo, servicio (lista), presupuesto mensual (número), mensaje |
| Hoja CRM | `recibido, nombre, correo, servicio, mensaje, presupuesto, prioridad, estado` |
| Asunto del correo | `[{prioridad}] Nuevo prospecto: {nombre} · {servicio}` |
| Consumo | 2 tareas por prospecto, de las 100 del mes. La revisión cada 15 min del plan gratis da la meta de «respuesta en menos de 15 minutos» |

## Prueba

Enviar 5 respuestas ficticias (2 con presupuesto ≥ 2.000.000) y verificar 5 filas en CRM y 5 correos, 2 de ellos marcados `[Alta]`.
