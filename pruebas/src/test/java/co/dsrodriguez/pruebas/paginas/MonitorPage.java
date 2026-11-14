package co.dsrodriguez.pruebas.paginas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.Select;

import java.math.BigDecimal;
import java.util.List;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/** Proyecto «Monitor de tasas y desembolsos» (datos públicos reales). */
public class MonitorPage extends Pagina {

    public static final String RUTA = "/proyectos/monitor-mercado/";
    private static final Pattern BILLONES = Pattern.compile("\\$([\\d.]+,\\d+) billones");

    public MonitorPage(WebDriver driver) {
        super(driver);
    }

    public MonitorPage abrir() {
        driver.get(PruebaBase.baseUrl() + RUTA);
        visible(By.cssSelector("#kpis .kpi"));
        return this;
    }

    public String avisoDatos() {
        return textoDe(By.cssSelector("[role=note]"));
    }

    public String mesSeleccionado() {
        return new Select(driver.findElement(By.id("fMes"))).getFirstSelectedOption().getText();
    }

    public int cantidadDeMeses() {
        return new Select(driver.findElement(By.id("fMes"))).getOptions().size();
    }

    /** Lee el primer indicador («$78,83 billones desembolsado…») y lo devuelve en billones. */
    public BigDecimal totalDesembolsadoBillones() {
        String texto = driver.findElement(By.cssSelector("#kpis .kpi .v")).getText();
        Matcher m = BILLONES.matcher(texto);
        if (!m.find()) throw new IllegalStateException("Indicador inesperado: " + texto);
        return new BigDecimal(m.group(1).replace(".", "").replace(",", "."));
    }

    /** Filas del top 10 (sin la fila de total): [rango, banco, monto, participación...]. */
    public List<List<String>> filasTop() {
        List<WebElement> filas = driver.findElements(By.cssSelector("#tTop tbody tr"));
        return filas.stream()
                .filter(f -> !f.getText().startsWith("Total"))
                .map(f -> f.findElements(By.tagName("td")).stream().map(WebElement::getText).toList())
                .toList();
    }

    public MonitorPage elegirBanco(String banco) {
        new Select(driver.findElement(By.id("fBanco"))).selectByVisibleText(banco);
        return this;
    }

    public String bancoResaltadoEnTop() {
        return driver.findElement(By.cssSelector("#tTop tr.foco td")).getText().replaceFirst("^\\d+\\s*", "");
    }
}
