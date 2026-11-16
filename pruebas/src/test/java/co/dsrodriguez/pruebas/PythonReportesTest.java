package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Reportes generados por las automatizaciones en Python: aviso de datos, indicadores y resultados esperados. */
@DisplayName("Reportes de las automatizaciones en Python")
class PythonReportesTest extends PruebaBase {

    private static final String PY = "/proyectos/automatizaciones/python/";

    private void abrir(String proyecto) {
        driver.get(baseUrl() + PY + proyecto + "/salida/reporte.html");
    }

    private List<String> kpis() {
        return driver.findElements(By.cssSelector(".kpi .v")).stream().map(WebElement::getText).toList();
    }

    @ParameterizedTest(name = "{0}: aviso «{1}» y cuatro indicadores")
    @CsvSource({"facturas-dian,ficticios", "conciliacion-bancaria,ficticios", "cobranza-cartera,ficticios", "monitor-trm,reales"})
    void avisoEIndicadores(String proyecto, String palabra) {
        abrir(proyecto);
        assertThat(driver.findElement(By.cssSelector("[role=note]")).getText()).contains(palabra);
        assertThat(kpis()).hasSize(4).allMatch(k -> !k.isBlank());
    }

    @Test
    @DisplayName("Facturas: detecta exactamente los cuatro errores sembrados")
    void facturasDetectaLosErrores() {
        abrir("facturas-dian");
        assertThat(driver.findElements(By.xpath("//h2[.='Alertas']/following-sibling::div[1]//tbody/tr"))).hasSize(4);
        assertThat(driver.getPageSource()).contains("DV del NIT inválido", "IVA no cuadra", "Total no cuadra", "Factura duplicada");
    }

    @Test
    @DisplayName("Conciliación: la prueba de saldos cuadra")
    void conciliacionCuadra() {
        abrir("conciliacion-bancaria");
        assertThat(kpis().get(3)).isEqualTo("Cuadra");
        List<WebElement> filas = driver.findElements(By.xpath("//h2[.='Prueba de la conciliación']/following-sibling::div[1]//tbody/tr"));
        String bancoAjustado = filas.get(2).findElements(By.tagName("td")).get(1).getText();
        String librosAjustado = filas.get(6).findElements(By.tagName("td")).get(1).getText();
        assertThat(bancoAjustado).isEqualTo(librosAjustado);
    }

    @Test
    @DisplayName("Cobranza: cada cliente en mora tiene su correo y el tono cambia con el tramo")
    void cobranzaCorreos() {
        abrir("cobranza-cartera");
        List<WebElement> enlaces = driver.findElements(By.linkText("Ver correo"));
        assertThat(enlaces).hasSize(Integer.parseInt(kpis().get(3)));
        String grave = driver.findElement(By.xpath("//tr[td/span[.='Más de 90 días']]//a")).getDomAttribute("href");
        driver.get(baseUrl() + PY + "cobranza-cartera/salida/" + grave);
        assertThat(driver.getPageSource()).contains("Último aviso antes de cobro prejurídico", "NO ENVIADO");
    }

    @Test
    @DisplayName("TRM: la gráfica responde al cursor con fecha y valor")
    void trmTooltip() {
        abrir("monitor-trm");
        WebElement zona = driver.findElement(By.id("trmZona"));
        new org.openqa.selenium.interactions.Actions(driver).moveToElement(zona).perform();
        WebElement tip = driver.findElement(By.id("trmTip"));
        assertThat(tip.isDisplayed()).isTrue();
        assertThat(tip.getText()).matches("\\d{2}/\\d{2}/\\d{4} · .*\\d.*");
    }
}
