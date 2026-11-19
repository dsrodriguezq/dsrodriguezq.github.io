/**
 * Detector de duplicados en un CRM · Google Apps Script
 *
 * Hoja esperada (fila 1 = encabezados):  ID | Cliente | Monto | Etapa
 * Uso: abre el Sheet → menú «🔍 Calidad de datos» → «Detectar duplicados».
 * No borra nada: marca las filas repetidas y dice cuánto inflan el embudo.
 */

function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('🔍 Calidad de datos')
    .addItem('Detectar duplicados', 'detectarDuplicados')
    .addItem('Limpiar marcas', 'limpiarMarcas')
    .addToUi();
}

// Normaliza el nombre: sin tildes, sin espacios extra, en minúsculas
function normalizar(texto) {
  return String(texto).normalize('NFD').replace(/[̀-ͯ]/g, '')
    .trim().replace(/\s+/g, ' ').toLowerCase();
}

function detectarDuplicados() {
  const hoja = SpreadsheetApp.getActiveSheet();
  limpiarMarcas();
  const datos = hoja.getDataRange().getValues();
  const colRevision = datos[0].length + 1;           // columna nueva al final
  hoja.getRange(1, colRevision).setValue('Revisión').setFontWeight('bold');

  const vistos = {};       // cliente normalizado → primera fila donde apareció
  let duplicados = 0, montoInflado = 0;

  for (let i = 1; i < datos.length; i++) {
    const [id, cliente, monto] = datos[i];
    if (!cliente) continue;
    const clave = normalizar(cliente);
    const fila = i + 1;                                // filas de la hoja empiezan en 1

    if (vistos[clave]) {
      duplicados++;
      montoInflado += Number(monto);
      hoja.getRange(fila, 1, 1, colRevision).setBackground('#FDE2E1');
      hoja.getRange(fila, colRevision).setValue(`⚠️ Duplicado de ${vistos[clave].id} (fila ${vistos[clave].fila})`);
    } else {
      vistos[clave] = { id, fila };
    }
  }

  SpreadsheetApp.flush();   // escribe los cambios en la hoja antes de mostrar la alerta
  const fmt = n => '$' + n.toLocaleString('es-CO');
  const texto = duplicados === 1 ? 'Se encontró 1 duplicado' : `Se encontraron ${duplicados} duplicados`;
  SpreadsheetApp.getUi().alert(duplicados
    ? `${texto}.\nEl embudo está inflado en ${fmt(montoInflado)}.`
    : '✅ No hay clientes duplicados.');
}

function limpiarMarcas() {
  const hoja = SpreadsheetApp.getActiveSheet();
  const encabezados = hoja.getRange(1, 1, 1, hoja.getLastColumn()).getValues()[0];
  const col = encabezados.indexOf('Revisión') + 1;
  if (col > 0) hoja.deleteColumn(col);
  hoja.getDataRange().setBackground(null);
  hoja.getRange(1, 1, 1, hoja.getLastColumn()).setBackground('#0b57d0'); // conserva el color del encabezado
}
