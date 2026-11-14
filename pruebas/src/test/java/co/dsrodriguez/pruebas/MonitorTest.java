package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.Http;
import co.dsrodriguez.pruebas.base.PruebaBase;
import co.dsrodriguez.pruebas.paginas.MicroIA;
import co.dsrodriguez.pruebas.paginas.MonitorPage;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.util.Arrays;
import java.util.List;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.within;

@DisplayName("Monitor de tasas y desembolsos (datos reales)")
class MonitorTest extends PruebaBase {

    private static final String CSV = MonitorPage.RUTA + "datos/looker/credito_mensual.csv";

    @Test
    @DisplayName("Carga datos reales y muestra la fuente oficial")
    void cargaDatosReales() {
        MonitorPage m = new MonitorPage(driver).abrir();
        assertThat(m.avisoDatos()).contains("Superintendencia Financiera").contains("datos.gov.co");
        assertThat(m.cantidadDeMeses()).isGreaterThanOrEqualTo(3);
    }

    @Test
    @DisplayName("Conciliación: el total del tablero coincide con la suma del CSV fuente del último mes")
    void totalCoincideConLaFuente() throws Exception {
        List<String[]> filas = Http.csv(baseUrl() + CSV);
        String[] encabezado = filas.get(0);
        int iFecha = Arrays.asList(encabezado).indexOf("fecha");
        int iMonto = Arrays.asList(encabezado).indexOf("monto_millones");
        String ultimo = filas.stream().skip(1).map(f -> f[iFecha]).max(String::compareTo).orElseThrow();
        BigDecimal totalCsv = filas.stream().skip(1).filter(f -> f[iFecha].equals(ultimo))
                .map(f -> new BigDecimal(f[iMonto])).reduce(BigDecimal.ZERO, BigDecimal::add)
                .divide(BigDecimal.valueOf(1_000_000), 2, RoundingMode.HALF_UP);

        BigDecimal totalTablero = new MonitorPage(driver).abrir().totalDesembolsadoBillones();

        assertThat(totalTablero).as("billones de pesos, mes %s", ultimo).isCloseTo(totalCsv, within(new BigDecimal("0.01")));
    }

    @Test
    @DisplayName("El top 10 trae 10 bancos ordenados de mayor a menor monto")
    void topOrdenado() {
        List<List<String>> top = new MonitorPage(driver).abrir().filasTop();
        assertThat(top).hasSize(10);
        List<Double> montos = top.stream().map(f -> aBillones(f.get(1))).toList();
        assertThat(montos).isSortedAccordingTo((a, b) -> Double.compare(b, a));
    }

    @Test
    @DisplayName("Al elegir otro banco, el top 10 lo resalta")
    void resaltaElBancoElegido() {
        MonitorPage m = new MonitorPage(driver).abrir().elegirBanco("Banco de Bogotá");
        assertThat(m.bancoResaltadoEnTop()).isEqualTo("Banco de Bogotá");
    }

    @ParameterizedTest(name = "La pestaña «{0}» muestra solo su panel")
    @ValueSource(strings = {"mer", "ban", "pla", "reg", "pos", "int"})
    void pestanas(String clave) {
        assertThat(new MonitorPage(driver).abrir().irAPestana(clave)).isTrue();
    }

    @Test
    @DisplayName("Micro IA del mercado: abre con sus cuatro secciones y Esc la minimiza")
    void microIA() {
        MicroIA ia = new MonitorPage(driver).abrir().microIA().abrir();
        assertThat(ia.secciones()).hasSize(4).anyMatch(s -> s.startsWith("POSICIÓN DE"))
                .contains("LECTURA Y ACCIONES SUGERIDAS");
        assertThat(ia.minimizarConEsc().minimizado()).isTrue();
    }

    /** "$23,02 billones" → 23.02 ; "$950,3 mil M" → 0.9503 ; "$800 M" → 0.0008 */
    private static double aBillones(String texto) {
        String n = texto.replace("$", "").replace(".", "").replace(",", ".").trim();
        if (n.endsWith("billones")) return Double.parseDouble(n.replace("billones", "").trim());
        if (n.endsWith("mil M")) return Double.parseDouble(n.replace("mil M", "").trim()) / 1_000;
        return Double.parseDouble(n.replace("M", "").trim()) / 1_000_000;
    }
}
