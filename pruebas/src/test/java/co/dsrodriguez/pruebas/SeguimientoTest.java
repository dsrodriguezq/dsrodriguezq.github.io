package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.PruebaBase;
import co.dsrodriguez.pruebas.paginas.MicroIA;
import co.dsrodriguez.pruebas.paginas.SeguimientoPage;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.junit.jupiter.api.Test;

import static org.assertj.core.api.Assertions.assertThat;

@DisplayName("Seguimiento comercial (datos ficticios)")
class SeguimientoTest extends PruebaBase {

    @Test
    @DisplayName("El aviso de datos 100 % ficticios es visible al cargar")
    void avisoDeDatosFicticios() {
        String aviso = new SeguimientoPage(driver).abrir().avisoDatos();
        assertThat(aviso).contains("100 % ficticios").contains("Banco Andino");
    }

    @ParameterizedTest(name = "La pestaña «{0}» muestra solo su panel")
    @ValueSource(strings = {"div", "zon", "com"})
    void pestanas(String clave) {
        assertThat(new SeguimientoPage(driver).abrir().irAPestana(clave)).isTrue();
    }

    @Test
    @DisplayName("Micro IA: abre con top 10, resumen operativo y acciones; Esc la minimiza y se restaura")
    void microIA() {
        MicroIA ia = new SeguimientoPage(driver).abrir().microIA().abrir();
        assertThat(ia.abierto()).isTrue();
        assertThat(ia.elFocoEstaEnElPanel()).as("el foco entra al panel (accesibilidad)").isTrue();
        assertThat(ia.secciones()).contains("TOP 10 · MENOR CUMPLIMIENTO AL CORTE", "RESUMEN OPERATIVO", "ACCIONES RECOMENDADAS");

        assertThat(ia.minimizarConEsc().minimizado()).isTrue();
        assertThat(ia.restaurar().abierto()).isTrue();
        assertThat(ia.minimizarConBoton().minimizado()).isTrue();
    }

    @ParameterizedTest(name = "La Micro IA se adapta al nivel «{0}»")
    @ValueSource(strings = {"div", "zon", "com"})
    void microIAPorNivel(String clave) {
        SeguimientoPage p = new SeguimientoPage(driver).abrir();
        p.irAPestana(clave);
        MicroIA ia = p.microIA().abrir();
        assertThat(ia.secciones()).contains("RESUMEN OPERATIVO");
    }
}
