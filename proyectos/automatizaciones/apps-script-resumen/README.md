# Google Sheets + Google Apps Script · Resumen de ventas por correo

> Proyecto propio. Las capturas son reales, con los datos personales ocultos. Los clientes y montos son de prueba.

## El problema

Para saber cómo van las ventas hay que abrir la hoja, filtrar por estado, sumar y escribir el correo. Es poco trabajo, pero se repite.

## La solución

Un script de Google Apps Script dentro del mismo Sheet. No necesita servidores, licencias ni herramientas externas: corre gratis en la cuenta de Google.

```
Sheet (Cliente | Monto | Estado) ─► Menú «📊 Automatizaciones» ─► Agrupa por estado ─► Correo HTML con la tabla y el total
```

## Piezas

| Pieza | Detalle |
|---|---|
| `onOpen()` | Crea el menú «📊 Automatizaciones» cada vez que se abre la hoja. No es una tarea programada: reacciona a un evento |
| `resumenVentas()` | Lee la hoja con `SpreadsheetApp`, agrupa los montos por estado y calcula el total |
| Correo | `GmailApp.sendEmail` con `htmlBody`: tabla con formato de pesos colombianos (`es-CO`) |
| Confirmación | Alerta en la hoja cuando el correo sale |

## Cómo usarlo

1. Crea un Google Sheet con los encabezados `Cliente | Monto | Estado` en la fila 1.
2. Ve a **Extensiones → Apps Script** y pega [`codigo/Codigo.gs`](codigo/Codigo.gs).
3. Guarda, recarga el Sheet y usa el menú **📊 Automatizaciones → Enviar resumen de ventas**.
4. La primera vez, Google pide autorizar el acceso a la hoja y a Gmail.

## Siguientes pasos

- Enviar el resumen a un destinatario que se lee de la propia hoja.
- Disparar el envío al recibir un formulario, en lugar de usar el menú.
