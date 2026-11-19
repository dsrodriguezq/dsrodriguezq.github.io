/**
 * Resumen de ventas por correo · Google Apps Script
 *
 * Hoja esperada (fila 1 = encabezados):  Cliente | Monto | Estado
 * Uso: abre el Sheet → menú «📊 Automatizaciones» → «Enviar resumen de ventas».
 */

// Se ejecuta solo cada vez que alguien abre el Sheet
function onOpen() {
  SpreadsheetApp.getUi()
    .createMenu('📊 Automatizaciones')
    .addItem('Enviar resumen de ventas', 'resumenVentas')
    .addToUi();
}

function resumenVentas() {
  const hoja = SpreadsheetApp.getActiveSheet();
  const datos = hoja.getDataRange().getValues().slice(1);

  // Agrupar montos por estado (como un groupby en pandas)
  const porEstado = {};
  let total = 0;
  datos.forEach(([cliente, monto, estado]) => {
    porEstado[estado] = (porEstado[estado] || 0) + Number(monto);
    total += Number(monto);
  });

  // Construir la tabla HTML
  const fmt = n => '$' + n.toLocaleString('es-CO');
  let filas = '';
  for (const estado in porEstado) {
    filas += `<tr><td style="padding:6px 12px">${estado}</td>
              <td style="padding:6px 12px;text-align:right">${fmt(porEstado[estado])}</td></tr>`;
  }
  const html = `
    <h2 style="font-family:Arial;color:#1a73e8">Resumen de ventas</h2>
    <table style="font-family:Arial;border-collapse:collapse" border="1">
      <tr style="background:#f1f3f4"><th style="padding:6px 12px">Estado</th><th style="padding:6px 12px">Monto</th></tr>
      ${filas}
      <tr style="font-weight:bold"><td style="padding:6px 12px">Total</td>
          <td style="padding:6px 12px;text-align:right">${fmt(total)}</td></tr>
    </table>
    <p style="font-family:Arial;color:#666">${datos.length} registros · enviado automáticamente</p>`;

  GmailApp.sendEmail(Session.getActiveUser().getEmail(), 'Resumen de ventas', '', { htmlBody: html });
  SpreadsheetApp.getUi().alert('✅ Resumen enviado a tu correo');
}
