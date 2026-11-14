package co.dsrodriguez.pruebas.base;

import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.extension.ExtendWith;
import org.openqa.selenium.WebDriver;
import org.openqa.selenium.chrome.ChromeDriver;
import org.openqa.selenium.chrome.ChromeOptions;

import java.time.Duration;

/**
 * Base de todas las pruebas: abre Chrome sin interfaz, define la URL del sitio
 * y guarda una captura de pantalla cuando una prueba falla.
 */
@ExtendWith(CapturaAlFallar.class)
public abstract class PruebaBase {

    protected WebDriver driver;

    public static String baseUrl() {
        String url = System.getProperty("baseUrl", "http://localhost:8000");
        if (url.isBlank() || url.startsWith("${")) url = "http://localhost:8000";
        return url.endsWith("/") ? url.substring(0, url.length() - 1) : url;
    }

    @BeforeEach
    void abrirNavegador() {
        ChromeOptions opciones = new ChromeOptions();
        opciones.addArguments("--headless=new", "--window-size=1440,1000", "--no-sandbox",
                "--disable-dev-shm-usage", "--lang=es-CO");
        driver = new ChromeDriver(opciones);
        driver.manage().timeouts().pageLoadTimeout(Duration.ofSeconds(30));
        CapturaAlFallar.registrar(driver);
    }

    @AfterEach
    void cerrarNavegador() {
        if (driver != null) driver.quit();
    }
}
