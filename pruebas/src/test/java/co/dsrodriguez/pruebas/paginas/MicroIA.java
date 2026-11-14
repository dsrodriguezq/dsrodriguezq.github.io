package co.dsrodriguez.pruebas.paginas;

import org.openqa.selenium.By;
import org.openqa.selenium.Keys;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.WebElement;
import org.openqa.selenium.interactions.Actions;
import org.openqa.selenium.support.ui.ExpectedConditions;
import org.openqa.selenium.support.ui.WebDriverWait;

import java.time.Duration;
import java.util.List;

/** Panel «Micro IA»: se abre con un botón, se minimiza con el botón o con Esc y se restaura desde la píldora. */
public class MicroIA {

    private static final By BOTON = By.id("iaBtn");
    private static final By PANEL = By.id("iaPanel");
    private static final By MINIMIZAR = By.id("iaMin");
    private static final By PILDORA = By.id("iaMini");
    private static final By RESTAURAR = By.id("iaRest");

    private final WebDriver driver;
    private final WebDriverWait espera;

    MicroIA(WebDriver driver) {
        this.driver = driver;
        this.espera = new WebDriverWait(driver, Duration.ofSeconds(10));
    }

    public MicroIA abrir() {
        espera.until(ExpectedConditions.elementToBeClickable(BOTON)).click();
        espera.until(ExpectedConditions.visibilityOfElementLocated(PANEL));
        return this;
    }

    public boolean abierto() {
        return driver.findElement(PANEL).isDisplayed()
                && "true".equals(driver.findElement(BOTON).getDomAttribute("aria-expanded"));
    }

    public boolean minimizado() {
        return !driver.findElement(PANEL).isDisplayed() && driver.findElement(PILDORA).isDisplayed();
    }

    public MicroIA minimizarConBoton() {
        driver.findElement(MINIMIZAR).click();
        espera.until(ExpectedConditions.visibilityOfElementLocated(PILDORA));
        return this;
    }

    public MicroIA minimizarConEsc() {
        new Actions(driver).sendKeys(Keys.ESCAPE).perform();
        espera.until(ExpectedConditions.visibilityOfElementLocated(PILDORA));
        return this;
    }

    public MicroIA restaurar() {
        driver.findElement(RESTAURAR).click();
        espera.until(ExpectedConditions.visibilityOfElementLocated(PANEL));
        return this;
    }

    public List<String> secciones() {
        return driver.findElement(PANEL).findElements(By.tagName("h4")).stream()
                .map(WebElement::getText).map(String::trim).toList();
    }

    public boolean elFocoEstaEnElPanel() {
        WebElement activo = driver.switchTo().activeElement();
        return driver.findElement(PANEL).findElements(By.xpath(".//*")).contains(activo);
    }
}
