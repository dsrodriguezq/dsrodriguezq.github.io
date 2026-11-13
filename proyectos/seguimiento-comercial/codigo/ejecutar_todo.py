"""Ejecuta el sistema completo de principio a fin: fuentes → pipeline → pronóstico → correos."""
import correos
import generar_fuentes
import pipeline
import pronostico

if __name__ == "__main__":
    print("\n=== 0. Fuentes ficticias ===")
    generar_fuentes.generar_todo()
    print("\n=== 1. Pipeline de consolidación ===")
    pipeline.main()
    print("\n=== 2. Pronóstico y segmentación ===")
    pronostico.main()
    print("\n=== 3. Correos de seguimiento ===")
    correos.main()
    print("\nListo. Abre index.html con un servidor local (python -m http.server) para ver el tablero.")
