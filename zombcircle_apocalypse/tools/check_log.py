# ======================================================================
# ARCHIVO: tools/check_log.py - herramienta para revisar la calidad de una bitacora
# ======================================================================
# QUE ES: un programita de consola (no forma parte del juego). Lee una carpeta de
# bitacoras y muestra cuantas sesiones se iniciaron y el reporte de calidad.
# COMO SE USA:  python tools/check_log.py [carpeta_de_logs]
# ======================================================================

"""Print session-start and data-quality counts for a log directory."""

# os: rutas de carpetas.
import os
# sys: leer lo que el usuario escribe en la terminal y ajustar rutas.
import sys

# Carpeta raiz del proyecto, agregada a la busqueda de Python para poder
# importar 'telemetry'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Lector de bitacora y reporte de calidad.
from telemetry import QualityReport, iter_events


# Funcion principal: recorre la bitacora y muestra los resultados.
def main(log_dir=None):
    """Stream a log directory and print its session and quality counts."""
    # Si no se indica carpeta, usa la carpeta 'logs' del proyecto.
    if log_dir is None:
        log_dir = os.path.join(BASE_DIR, "logs")

    # Preparamos el reporte y contamos cuantos SESSION_START hay.
    report = QualityReport()
    sessions_started = 0
    for event in iter_events(log_dir, report=report):
        if event["event_type"] == "SESSION_START":
            sessions_started += 1

    # Mostramos el conteo y el reporte de calidad.
    print("Sesiones iniciadas: %s" % format(sessions_started, ","))
    report.print_report()


# Solo se ejecuta cuando abres este archivo directamente (no al importarlo).
if __name__ == "__main__":
    selected_log_dir = sys.argv[1] if len(sys.argv) > 1 else None
    main(selected_log_dir)