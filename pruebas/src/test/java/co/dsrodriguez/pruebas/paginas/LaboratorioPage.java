package co.dsrodriguez.pruebas.paginas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

/** Laboratorio de automatizaciones: simulador de la bandeja de Make. */
public class LaboratorioPage extends Pagina {

    public static final String RUTA = "/proyectos/automatizaciones/";

    public LaboratorioPage(WebDriver driver) {
        super(driver);
    }

    public LaboratorioPage abrir() {
        driver.get(PruebaBase.baseUrl() + RUTA);
        visible(By.id("run"));
        return this;
    }

    public int proyectos() {
        return driver.findElements(By.cssSelector("article.proj")).size();
    }

    public int solicitudesEnBandeja() {
        return driver.findElements(By.cssSelector("#inbox > div")).size();
    }

    /** Procesa las solicitudes y espera a que todas hayan llegado a una ruta. */
    public LaboratorioPage procesar() {
        driver.findElement(By.id("run")).click();
        int total = solicitudesEnBandeja();
        espera.until(d -> d.findElements(By.cssSelector(".lane .chip.in")).size() == total);
        return this;
    }

    public LaboratorioPage reiniciar() {
        driver.findElement(By.id("reset")).click();
        return this;
    }

    /** Ruta → nombres de las personas que quedaron en ella. */
    public Map<String, List<String>> resultado() {
        return driver.findElements(By.cssSelector(".lane")).stream().collect(Collectors.toMap(
                l -> l.getDomAttribute("data-r"),
                l -> l.findElements(By.cssSelector(".chip")).stream()
                        .map(c -> c.getText().split("\n")[0].trim()).toList()));
    }

    public int contador(String ruta) {
        WebElement span = driver.findElement(By.cssSelector(".lane[data-r='" + ruta + "'] h4 span"));
        return Integer.parseInt(span.getText().trim());
    }

    public boolean botonProcesarHabilitado() {
        return driver.findElement(By.id("run")).isEnabled();
    }
}
