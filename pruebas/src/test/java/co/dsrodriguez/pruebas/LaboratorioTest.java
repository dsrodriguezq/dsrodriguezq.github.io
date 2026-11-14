package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import co.dsrodriguez.pruebas.paginas.LaboratorioPage;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;

import java.util.List;
import java.util.Map;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("Laboratorio de automatizaciones")
class LaboratorioTest extends PruebaBase {

    @Test
    @DisplayName("Muestra las seis automatizaciones y el aviso de datos ficticios")
    void muestraLosSeisProyectos() {
        LaboratorioPage lab = new LaboratorioPage(driver).abrir();
        assertThat(lab.proyectos()).isEqualTo(6);
        assertThat(driver.getPageSource()).contains("Datos 100 % ficticios");
    }

    @Test
    @DisplayName("El simulador reparte las 9 solicitudes según las reglas del escenario de Make")
    void clasificaSegunLasReglas() {
        LaboratorioPage lab = new LaboratorioPage(driver).abrir();
        assertThat(lab.solicitudesEnBandeja()).isEqualTo(9);

        Map<String, List<String>> r = lab.procesar().resultado();

        assertThat(r.get("Cotizaciones")).containsExactlyInAnyOrder("Laura Méndez", "Julián Rojas", "Valentina Ruiz");
        assertThat(r.get("Soporte")).containsExactlyInAnyOrder("Andrés Pardo", "Sofía Valencia");
        assertThat(r.get("Quejas")).containsExactlyInAnyOrder("Camila Ortiz", "Felipe Gómez", "Daniela Herrera");
        assertThat(r.get("Otros")).containsExactly("Mateo Castro");
        assertThat(lab.contador("Quejas")).isEqualTo(3);
        assertThat(lab.botonProcesarHabilitado()).as("no se puede procesar dos veces").isFalse();
    }

    @Test
    @DisplayName("Casos trampa: «COTIZACION » se limpia y un «reclamo» de soporte se escala a Quejas")
    void casosTrampa() {
        Map<String, List<String>> r = new LaboratorioPage(driver).abrir().procesar().resultado();
        assertThat(r.get("Cotizaciones")).contains("Valentina Ruiz");
        assertThat(r.get("Quejas")).contains("Felipe Gómez");
        assertThat(r.get("Soporte")).doesNotContain("Felipe Gómez");
    }

    @Test
    @DisplayName("Reiniciar vacía las rutas y vuelve a habilitar el botón")
    void reiniciar() {
        LaboratorioPage lab = new LaboratorioPage(driver).abrir().procesar().reiniciar();
        assertThat(lab.resultado().values()).allMatch(List::isEmpty);
        assertThat(lab.contador("Cotizaciones")).isZero();
        assertThat(lab.botonProcesarHabilitado()).isTrue();
    }
}
