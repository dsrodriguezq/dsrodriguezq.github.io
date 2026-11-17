package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.openqa.selenium.By;
import org.openqa.selenium.WebElement;

import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;

/** Informes por banco generados con R Markdown. */
@DisplayName("Informes por banco (R Markdown)")
class InformesRTest extends PruebaBase {

    private static final String RUTA = "/proyectos/informe-bancos-r/informes/";

    @Test
    @DisplayName("El índice enlaza un informe por banco, ordenados de mayor a menor monto")
    void indice() {
        driver.get(baseUrl() + RUTA);
        int generados = Integer.parseInt(driver.findElement(By.cssSelector(".kpi .v")).getText().trim());
        List<WebElement> filas = driver.findElements(By.cssSelector("table.tabla tbody tr"));
        assertThat(filas).hasSize(generados).hasSizeGreaterThan(10);
        assertThat(filas.get(0).findElement(By.cssSelector("td")).getText()).isEqualTo("1");
    }

    @Test
    @DisplayName("El informe de un banco coincide con su fila del índice y trae sus tres gráficas")
    void informeCoincideConIndice() {
        driver.get(baseUrl() + RUTA);
        WebElement fila = driver.findElements(By.cssSelector("table.tabla tbody tr")).get(0);
        String banco = fila.findElement(By.tagName("a")).getText();
        String monto = fila.findElements(By.tagName("td")).get(2).getText();
        fila.findElement(By.tagName("a")).click();

        assertThat(driver.findElement(By.cssSelector("h1")).getText()).startsWith(banco);
        assertThat(driver.findElement(By.cssSelector(".kpi .v")).getText()).isEqualTo(monto);
        assertThat(driver.findElement(By.cssSelector("[role=note]")).getText()).contains("Datos públicos reales");
        assertThat(driver.findElements(By.cssSelector("img[alt]"))).hasSizeGreaterThanOrEqualTo(3);
        assertThat(driver.findElements(By.cssSelector("table.tabla tbody tr"))).isNotEmpty();
    }

    @Test
    @DisplayName("La lectura del mes está redactada y sin valores vacíos")
    void lecturaSinVacios() {
        driver.get(baseUrl() + RUTA + "banco-de-occidente.html");
        String texto = driver.findElement(By.tagName("body")).getText();
        assertThat(texto).contains("Lectura del mes", "desembolsó").doesNotContain("NA %", "NaN", "<U+");
    }
}
