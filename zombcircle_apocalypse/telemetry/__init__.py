# ======================================================================
# ARCHIVO: telemetry/__init__.py - la 'puerta de entrada' del paquete telemetry
# ======================================================================
# QUE ES: en Python, una carpeta con un archivo __init__.py se vuelve un 'paquete'.
# Este archivo solo decide que cosas de la carpeta telemetry se pueden importar
# facilmente desde fuera: el escritor de bitacora, el lector y el reporte de calidad.
# (telemetria = registrar lo que pasa en el juego para analizarlo despues).
# ======================================================================

"""Paquete telemetry: bitacora de eventos del juego.

Exporta la escritura (TelemetryWriter) y la lectura (iter_events,
parse_line, NUMERIC_KEYS y QualityReport.
"""
# Trae el ESCRITOR de bitacora (guarda eventos en archivos).
from .writer import TelemetryWriter
# Trae el LECTOR (lee los archivos y entrega eventos uno por uno).
from .reader import iter_events, parse_line, NUMERIC_KEYS
# Trae el REPORTE DE CALIDAD (cuenta lineas buenas y malas).
from .quality import QualityReport

# Lista oficial de lo que se exporta desde este paquete.
__all__ = ["TelemetryWriter", "iter_events", "parse_line", "NUMERIC_KEYS",
		   "QualityReport"]
