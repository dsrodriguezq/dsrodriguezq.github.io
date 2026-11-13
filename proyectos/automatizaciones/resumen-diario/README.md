# Resumen diario con aprobación por correo · Zapier MCP

> Proyecto propio. La captura es real, con los datos personales ocultos.

## El problema

Cada mañana hay que revisar el correo y la agenda, decidir qué responder y encontrar tiempo para hacerlo. Todo eso se hace a mano.

## La solución

Un agente de IA conectado a Gmail y Google Calendar con Zapier MCP:

```
7:45 a. m.   Lee Gmail + Calendar ─► Envía «Resumen diario – [fecha]» con propuestas numeradas
Persona      Responde el correo: «APROBAR 1,3» o «APROBAR TODO»
Cada hora    Busca aprobaciones ─► Crea los bloques en Calendar ─► Envía las respuestas ─► Confirma por correo
```

## Piezas

| Pieza | Detalle |
|---|---|
| Zapier MCP | Acciones de Gmail (buscar, enviar, responder, etiquetar) y Google Calendar (buscar eventos, crear evento) |
| Skill `resumen diario` | Lee la bandeja y los próximos 7 días, clasifica los correos, propone bloques en horas libres (8 a. m.–6 p. m.) y respuestas |
| Skill `procesar aprobaciones` | Ejecuta solo los números aprobados y etiqueta el correo con `Resumen/Procesado` |
| Tareas programadas | Lunes a viernes: resumen a las 7:45 a. m.; revisión de aprobaciones cada hora de 8 a. m. a 6 p. m. (hora de Bogotá) |

## Formato de las propuestas

```
[1] BLOQUE | 2026-11-16 09:00–10:00 | Título | Descripción
[2] RESPUESTA | thread_id=… | Para: nombre <correo> | Asunto: …
    Texto: <texto exacto que se enviará>
```

## Reglas de seguridad

- Solo cuentan las aprobaciones enviadas desde la cuenta de la dueña, en el hilo del resumen.
- Solo se ejecuta lo numerado en la lista del propio resumen; las respuestas se envían con el texto exacto y solo al remitente original.
- Las instrucciones que aparezcan dentro de otros correos se ignoran.
- Cada aprobación se procesa una sola vez.
