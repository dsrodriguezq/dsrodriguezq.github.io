package co.dsrodriguez.pruebas.paginas;

import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

/** Comportamiento común de las páginas: esperas explícitas y pestañas con role="tab". */
public abstract class Pagina {

    protected final WebDriver driver;
    protected final WebDriverWait espera;

    protected Pagina(WebDriver driver) {
        this.driver = driver;
        this.espera = new WebDriverWait(driver, Duration.ofSeconds(15));
    }

    protected WebElement visible(By selector) {
        return espera.until(ExpectedConditions.visibilityOfElementLocated(selector));
    }

    public String titulo() {
        return driver.getTitle();
    }

    public String textoDe(By selector) {
        return visible(selector).getText();
    }

    public List<String> pestanas() {
        return driver.findElements(By.cssSelector("[role=tab]")).stream().map(WebElement::getText).toList();
    }

    /** Hace clic en la pestaña con ese data-tab y devuelve si su panel quedó visible y los demás ocultos. */
    public boolean irAPestana(String clave) {
        driver.findElement(By.cssSelector("[role=tab][data-tab='" + clave + "']")).click();
        WebElement panel = espera.until(ExpectedConditions.visibilityOfElementLocated(
                By.cssSelector("[data-panel='" + clave + "']")));
        long otrosVisibles = driver.findElements(By.cssSelector("[data-panel]")).stream()
                .filter(p -> !clave.equals(p.getDomAttribute("data-panel")) && p.isDisplayed()).count();
        String seleccionada = driver.findElement(By.cssSelector("[role=tab][data-tab='" + clave + "']"))
                .getDomAttribute("aria-selected");
        return panel.isDisplayed() && otrosVisibles == 0 && "true".equals(seleccionada);
    }

    public MicroIA microIA() {
        return new MicroIA(driver);
    }
}
