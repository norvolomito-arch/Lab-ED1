"""Lectura robusta de la bitacora de eventos (Persona 1).

Interfaz publica (la usan las Personas 2 y 3):

    iter_events(log_dir, report=None)  -> generador de eventos
    parse_line(linea)                  -> evento o None

Cada evento es un diccionario:

    {"timestamp": float, "session_id": str,
     "event_type": str, "params": dict}

Los valores de ``params`` cuya clave esta en ``NUMERIC_KEYS`` ya vienen
convertidos a int/float; los demas quedan como str (ya des-escapados).
Se convierte solo por NOMBRE de clave para que un jugador llamado "123"
no se vuelva el entero 123.

Politica: toda linea invalida se CUENTA y se DESCARTA; nada lanza excepcion.

Una linea es corrupta si:
  - esta vacia o solo tiene espacios;
  - no tiene exactamente 4 campos separados por "|";
  - el timestamp no es un numero finito >= 0, o session_id/event_type
    estan vacios;
  - algun parametro no tiene "=", tiene clave o valor vacio, o repite clave;
  - una clave numerica (score, level, ...) trae un valor no convertible;
  - es la ultima linea de un archivo y no termina en "\\n" (truncada por un
    cierre abrupto): aunque tenga 4 campos, podria estar cortada en medio
    de un valor (p. ej. ``result=de``), y la regla 1 del formato exige que
    toda linea termine en salto de linea. El writer SIEMPRE lo escribe.

Protocolo del reporte de calidad (``QualityReport`` en quality.py). iter_events
solo llama estos metodos, asi el lector no depende de la clase:

    report.add_file()          un archivo se abrio para leerlo
    report.add_line()          se leyo una linea (valida o no)
    report.add_valid(event)    la linea fue un evento valido
    report.add_corrupt()       la linea fue corrupta
    report.finish()            termino el recorrido COMPLETO de todos los
                               archivos (no se llama si el consumidor
                               abandona el generador a la mitad)
"""
import math

from .common import list_log_files, unescape

NUMERIC_KEYS = ("score", "level", "duration", "amount", "wave", "time")
MAX_LINE_LENGTH = 4096   # una linea real mide < 300; evita basura enorme


def _to_number(text):
    """Convierte ``text`` a int o float finito; lanza ValueError si no."""
    text = text.strip()
    # int()/float() aceptan cosas raras ("1_000", digitos no ASCII): se
    # rechazan para que el formato sea estricto.
    if not text or not text.isascii() or "_" in text:
        raise ValueError(text)
    try:
        return int(text)
    except ValueError:
        number = float(text)
        if not math.isfinite(number):   # nan, inf
            raise ValueError(text)
        return number


def _parse_params(field):
    """Cuarto campo -> dict de parametros. Lanza ValueError si es corrupto."""
    if not field.strip():
        return {}                       # evento sin parametros
    params = {}
    for piece in field.split(";"):
        key, sep, value = piece.partition("=")
        # sin "=", clave/valor vacios, "=" suelto dentro del valor (el writer
        # lo escapa como %3D, asi que un "=" crudo indica linea danada)
        if not sep or not key.strip() or not value.strip() or "=" in value:
            raise ValueError(piece)
        key = unescape(key)
        if key in params:
            raise ValueError(key)
        params[key] = _to_number(value) if key in NUMERIC_KEYS else unescape(value)
    return params


def parse_line(linea):
    """Convierte una linea de la bitacora en evento; None si es corrupta.

    Nunca lanza excepciones. Acepta la linea con o sin salto final (la
    regla de "ultima linea sin \\n" la aplica iter_events, que es quien
    sabe que linea es la ultima del archivo).
    """
    if not isinstance(linea, str) or len(linea) > MAX_LINE_LENGTH:
        return None
    text = linea.rstrip("\r\n")
    if not text.strip():
        return None
    parts = text.split("|")
    if len(parts) != 4:
        return None
    try:
        timestamp = float(_to_number(parts[0]))
        if timestamp < 0:
            return None
        if not parts[1].strip() or not parts[2].strip():
            return None
        params = _parse_params(parts[3])
    except (ValueError, OverflowError):
        return None
    return {"timestamp": timestamp,
            "session_id": unescape(parts[1]),
            "event_type": unescape(parts[2]),
            "params": params}


def iter_events(log_dir, report=None):
    """Recorre TODOS los events_NNN.log de ``log_dir`` y entrega eventos.

    - Orden NUMERICO de archivos (events_1000 despues de events_999).
    - Lectura perezosa: ``for linea in f``; en memoria hay una linea a la
      vez, sin importar el tamano de la bitacora.
    - Carpeta inexistente o vacia: no entrega nada y no falla.
    - Bytes que no son UTF-8 valido se reemplazan (errors="replace") en vez
      de lanzar UnicodeDecodeError; esa linea acabara siendo corrupta.
    - Un archivo que no se puede abrir o leer se salta; los demas siguen.
    """
    for path in list_log_files(log_dir):
        try:
            f = open(path, "r", encoding="utf-8", errors="replace")
        except OSError:
            continue
        with f:
            if report is not None:
                report.add_file()
            try:
                for linea in f:
                    if report is not None:
                        report.add_line()
                    # Solo la ultima linea de un archivo puede carecer de
                    # "\n": es una linea truncada (ver docstring del modulo).
                    event = parse_line(linea) if linea.endswith("\n") else None
                    if event is None:
                        if report is not None:
                            report.add_corrupt()
                        continue
                    if report is not None:
                        report.add_valid(event)
                    yield event
            except OSError:
                continue            # lectura interrumpida: se sigue al siguiente
    if report is not None:
        report.finish()
