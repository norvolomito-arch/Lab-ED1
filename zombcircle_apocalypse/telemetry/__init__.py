"""Paquete telemetry: bitacora de eventos del juego.

Exporta la escritura (TelemetryWriter) y la lectura (iter_events,
parse_line, NUMERIC_KEYS y QualityReport.
"""
from .writer import TelemetryWriter
from .reader import iter_events, parse_line, NUMERIC_KEYS
from .quality import QualityReport

__all__ = ["TelemetryWriter", "iter_events", "parse_line", "NUMERIC_KEYS",
		   "QualityReport"]
