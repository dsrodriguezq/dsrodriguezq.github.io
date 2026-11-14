# Pruebas de punta a punta del portafolio · Selenium + Java

![Pruebas E2E](https://github.com/dsrodriguezq/dsrodriguezq.github.io/actions/workflows/pruebas.yml/badge.svg)

Suite de pruebas automatizadas sobre mis propios proyectos. Simula lo que hace una persona en el navegador (clics, filtros, teclado) y rastrea el sitio para encontrar enlaces rotos. También concilia lo que muestra un tablero contra su fuente de datos.

## Qué cubre (31 pruebas)

| Suite | Qué verifica |
|---|---|
| `LaboratorioTest` | El simulador de Make reparte las 9 solicitudes en la ruta correcta, incluidos los casos trampa («COTIZACION » con espacios y un reclamo enviado como soporte), y se puede reiniciar. |
| `SeguimientoTest` | Aviso de datos ficticios visible; cada pestaña muestra solo su panel; la Micro IA abre con sus tres secciones en todos los niveles, lleva el foco al panel, se minimiza con Esc y se restaura. |
| `MonitorTest` | **Conciliación de datos:** el total desembolsado del tablero coincide con la suma del CSV fuente del último mes. El top 10 viene ordenado, resalta el banco elegido, las 6 pestañas funcionan y la Micro IA del mercado tiene sus cuatro secciones. |
| `EnlacesTest` | **Web scraping con Jsoup:** extrae todos los enlaces, imágenes, estilos y scripts de cada página y confirma que ninguno esté roto. También revisa que las imágenes tengan texto alternativo, que haya un solo `h1` y que el idioma sea español. |

## Cómo está construida

- **Java 21 + Selenium 4 + JUnit 5 + AssertJ.** Selenium Manager descarga el driver solo.
- **Page Object Model** (`paginas/`): cada página expone acciones de negocio (`procesar()`, `abrir()`, `minimizarConEsc()`), no selectores.
- **Esperas explícitas**, nunca `Thread.sleep`.
- **Captura de pantalla automática** cuando una prueba falla (`target/capturas/`).
- **Integración continua:** GitHub Actions corre la suite en cada cambio, sobre una copia local del sitio, y cada lunes sobre el sitio publicado. El resumen sale como tabla en la pestaña Actions.

## Correrla en tu equipo

Requiere Java 21, Maven y Chrome.

```bash
# Contra el sitio publicado
mvn test -f pruebas/pom.xml -DbaseUrl=https://dsrodriguezq.github.io

# Contra una copia local (desde la raíz del repositorio)
python -m http.server 8000
mvn test -f pruebas/pom.xml
```
