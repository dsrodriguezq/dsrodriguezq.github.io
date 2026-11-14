package co.dsrodriguez.pruebas.base;

import org.junit.jupiter.api.extension.AfterTestExecutionCallback;
import org.junit.jupiter.api.extension.ExtensionContext;
import org.openqa.selenium.OutputType;
import org.openqa.selenium.TakesScreenshot;
import org.openqa.selenium.WebDriver;

import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.StandardCopyOption;

/**
 * Si una prueba falla, guarda una captura en target/capturas para revisarla en GitHub Actions.
 * Corre justo después del método de prueba y antes de @AfterEach, cuando el navegador sigue abierto.
 */
public class CapturaAlFallar implements AfterTestExecutionCallback {

    private static final ThreadLocal<WebDriver> ACTUAL = new ThreadLocal<>();

    static void registrar(WebDriver driver) {
        ACTUAL.set(driver);
    }

    @Override
    public void afterTestExecution(ExtensionContext contexto) {
        if (contexto.getExecutionException().isEmpty()) return;
        WebDriver driver = ACTUAL.get();
        if (!(driver instanceof TakesScreenshot ts)) return;
        try {
            Path carpeta = Path.of("target", "capturas");
            Files.createDirectories(carpeta);
            String nombre = contexto.getRequiredTestClass().getSimpleName() + "_" +
                    contexto.getRequiredTestMethod().getName() + ".png";
            Files.copy(ts.getScreenshotAs(OutputType.FILE).toPath(), carpeta.resolve(nombre),
                    StandardCopyOption.REPLACE_EXISTING);
        } catch (Exception e) {
            System.err.println("No se pudo guardar la captura: " + e.getMessage());
        }
    }
}
