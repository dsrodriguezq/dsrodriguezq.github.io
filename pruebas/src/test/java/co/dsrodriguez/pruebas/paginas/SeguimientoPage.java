package co.dsrodriguez.pruebas.paginas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import org.openqa.selenium.By;
import org.openqa.selenium.WebDriver;

/** Proyecto «Seguimiento comercial» (Banco Andino, datos ficticios). */
public class SeguimientoPage extends Pagina {

    public static final String RUTA = "/proyectos/seguimiento-comercial/";

    public SeguimientoPage(WebDriver driver) {
        super(driver);
    }

    public SeguimientoPage abrir() {
        driver.get(PruebaBase.baseUrl() + RUTA);
        visible(By.id("iaBtn"));
        return this;
    }

    public String avisoDatos() {
        return textoDe(By.cssSelector("[role=note]"));
    }
}
