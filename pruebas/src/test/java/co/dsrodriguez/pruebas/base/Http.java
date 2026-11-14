package co.dsrodriguez.pruebas.base;

import java.io.IOException;
import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.ArrayList;
import java.util.List;

/** Utilidades HTTP y un lector de CSV sencillo (respeta campos entre comillas). */
public final class Http {

    private static final HttpClient CLIENTE = HttpClient.newBuilder()
            .followRedirects(HttpClient.Redirect.NORMAL)
            .connectTimeout(Duration.ofSeconds(15))
            .build();

    private Http() {}

    public static int estado(String url) throws IOException, InterruptedException {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(20))
                .method("GET", HttpRequest.BodyPublishers.noBody())
                .header("User-Agent", "pruebas-portafolio (+https://dsrodriguezq.github.io)").build();
        return CLIENTE.send(req, HttpResponse.BodyHandlers.discarding()).statusCode();
    }

    public static String texto(String url) throws IOException, InterruptedException {
        HttpRequest req = HttpRequest.newBuilder(URI.create(url)).timeout(Duration.ofSeconds(30)).build();
        HttpResponse<String> r = CLIENTE.send(req, HttpResponse.BodyHandlers.ofString());
        if (r.statusCode() != 200) throw new IOException("HTTP " + r.statusCode() + " en " + url);
        return r.body();
    }

    public static List<String[]> csv(String url) throws IOException, InterruptedException {
        List<String[]> filas = new ArrayList<>();
        for (String linea : texto(url).split("\r?\n")) {
            if (linea.isBlank()) continue;
            List<String> campos = new ArrayList<>();
            StringBuilder actual = new StringBuilder();
            boolean comillas = false;
            for (int i = 0; i < linea.length(); i++) {
                char c = linea.charAt(i);
                if (c == '"') {
                    if (comillas && i + 1 < linea.length() && linea.charAt(i + 1) == '"') { actual.append('"'); i++; }
                    else comillas = !comillas;
                } else if (c == ',' && !comillas) {
                    campos.add(actual.toString()); actual.setLength(0);
                } else actual.append(c);
            }
            campos.add(actual.toString());
            filas.add(campos.toArray(String[]::new));
        }
        return filas;
    }
}
