package co.dsrodriguez.pruebas;

import co.dsrodriguez.pruebas.base.Http;
import co.dsrodriguez.pruebas.base.PruebaBase;
import org.jsoup.Jsoup;
import org.jsoup.nodes.Document;
import org.jsoup.nodes.Element;
import org.junit.jupiter.api.DisplayName;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

import java.net.URI;
import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;

import static org.assertj.core.api.Assertions.assertThat;

/**
 * Web scraping con Jsoup: lee cada página como lo haría un rastreador, extrae todos los enlaces,
 * imágenes, hojas de estilo y scripts del propio sitio, y verifica que ninguno esté roto.
 * También revisa reglas de calidad: imágenes con texto alternativo y un solo h1.
 */
@DisplayName("Rastreo del sitio: enlaces y recursos")
class EnlacesTest {

    @ParameterizedTest(name = "{0}: ningún enlace o recurso interno roto")
    @ValueSource(strings = {"/", "/proyectos/seguimiento-comercial/", "/proyectos/monitor-mercado/", "/proyectos/automatizaciones/"})
    void sinEnlacesRotos(String ruta) throws Exception {
        String base = PruebaBase.baseUrl();
        Document doc = Jsoup.connect(base + ruta).userAgent("pruebas-portafolio").get();

        Set<String> internos = new LinkedHashSet<>();
        for (Element e : doc.select("a[href], img[src], link[href], script[src], iframe[src]")) {
            String url = e.hasAttr("src") ? e.absUrl("src") : e.absUrl("href");
            if (url.isEmpty() || url.startsWith("mailto:") || url.startsWith("javascript:")) continue;
            if (!url.startsWith(base)) continue;
            internos.add(URI.create(url.split("#")[0]).toString());
        }

        List<String> rotos = new ArrayList<>();
        for (String url : internos) {
            int estado = Http.estado(url);
            if (estado >= 400) rotos.add(estado + " " + url);
        }
        assertThat(internos).as("la página debe tener enlaces internos").isNotEmpty();
        assertThat(rotos).as("enlaces rotos en %s", ruta).isEmpty();
    }

    @ParameterizedTest(name = "{0}: imágenes con texto alternativo y un solo h1")
    @ValueSource(strings = {"/", "/proyectos/seguimiento-comercial/", "/proyectos/monitor-mercado/", "/proyectos/automatizaciones/"})
    void accesibilidadBasica(String ruta) throws Exception {
        Document doc = Jsoup.connect(PruebaBase.baseUrl() + ruta).userAgent("pruebas-portafolio").get();
        List<String> sinAlt = doc.select("img:not([alt])").eachAttr("src");
        assertThat(sinAlt).as("imágenes sin alt").isEmpty();
        assertThat(doc.select("h1")).as("encabezados h1").hasSize(1);
        assertThat(doc.select("html").attr("lang")).isEqualTo("es");
    }
}
