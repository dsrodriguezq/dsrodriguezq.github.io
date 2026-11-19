# Detector de duplicados en un CRM · Google Sheets + Google Apps Script

> Proyecto propio. La captura es real. Los clientes y montos del CRM son de prueba.

## El problema

En los CRM que se llevan en una hoja de cálculo, el mismo cliente termina registrado dos veces: con otra etapa, con una tilde de más o con un espacio al final. Cada duplicado infla el embudo de ventas y distorsiona el pronóstico.

## La solución

Un script de Google Apps Script dentro del mismo Sheet, con un menú «🔍 Calidad de datos»:

```
CRM (ID | Cliente | Monto | Etapa) ─► Normaliza nombres ─► Detecta repetidos ─► Marca la fila + columna «Revisión» ─► Alerta con el monto inflado
```

En el CRM de prueba encuentra a «Agencia Viajes Rumbo» registrada como P-012 y P-013, y avisa que el embudo está inflado en $5.300.000.

## Piezas

| Pieza | Detalle |
|---|---|
| `normalizar()` | Quita tildes, espacios repetidos y mayúsculas, para que «Agencia  Viájes Rumbo » y «agencia viajes rumbo» cuenten como el mismo cliente |
| `detectarDuplicados()` | Recorre el CRM con un diccionario de clientes vistos, pinta las filas repetidas y escribe a qué registro duplican |
| `SpreadsheetApp.flush()` | Aplica los cambios en la hoja antes de mostrar la alerta, para que lo que se ve coincida con lo que hizo el script |
| `limpiarMarcas()` | Deshace todo: quita la columna «Revisión» y los colores |

## Decisiones de diseño

- **No borra registros.** Decidir cuál de los dos conservar es una decisión de negocio, no del script.
- **Se puede deshacer** con un clic desde el mismo menú.
- **Reacciona a un clic**, no a una hora fija: no necesita tareas programadas.

## Cómo usarlo

1. En tu CRM de Google Sheets, ve a **Extensiones → Apps Script** y pega [`codigo/Codigo.gs`](codigo/Codigo.gs).
2. Guarda, recarga el Sheet y usa **🔍 Calidad de datos → Detectar duplicados**.
3. La primera vez, Google pide autorizar el acceso a la hoja.
