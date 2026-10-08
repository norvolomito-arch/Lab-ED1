"""Utilidades compartidas por el escritor y el lector de la bitacora (Persona 1).

Aqui viven dos cosas que ambos modulos deben entender IGUAL:

1. La estrategia de escape de valores (escape / unescape).
2. La convencion de nombres de archivo ``events_NNN.log`` y su orden.

ESTRATEGIA DE ESCAPE (para el informe)
--------------------------------------
Un valor de texto podria contener los delimitadores del formato
(``|`` separa campos, ``;`` separa parametros, ``=`` separa clave y valor)
o un salto de linea. Si se escribiera tal cual, la linea cambiaria de
significado: ``player=a|b`` produciria 5 campos y el lector la descartaria
como corrupta (o, peor, leeria un parametro que no existe).

Solucion: "percent-encoding" (como las URL). Cada caracter peligroso se
reemplaza por ``%`` + su codigo hexadecimal, y ``%`` tambien se escapa para
que la operacion sea reversible sin ambiguedad:

    %  ->  %25        |  ->  %7C        ;  ->  %3B
    =  ->  %3D       \\n ->  %0A        \\r ->  %0D

Ejemplo:  "a|b;c=d%"  ->  "a%7Cb%3Bc%3Dd%25"   (y unescape lo devuelve igual)
"""
import os

LOG_PREFIX = "events_"
LOG_SUFFIX = ".log"

# Orden importa: "%" va primero al escapar para no re-escapar los codigos
# que se acaban de generar; al des-escapar se recorre al reves.
_ESCAPES = (("%", "%25"), ("|", "%7C"), (";", "%3B"), ("=", "%3D"),
            ("\n", "%0A"), ("\r", "%0D"))


def escape(value):
    """Devuelve ``str(value)`` sin delimitadores ni saltos de linea."""
    text = str(value)
    for char, code in _ESCAPES:
        text = text.replace(char, code)
    return text


def unescape(text):
    """Inversa exacta de :func:`escape`."""
    for char, code in reversed(_ESCAPES):
        text = text.replace(code, char)
    return text


def log_filename(index):
    """Nombre del archivo numero ``index``: 1 -> ``events_001.log``."""
    return "%s%03d%s" % (LOG_PREFIX, index, LOG_SUFFIX)


def log_index(name):
    """Numero N de un archivo ``events_N.log``; None si no sigue el patron."""
    name = os.path.basename(name)
    if not (name.startswith(LOG_PREFIX) and name.endswith(LOG_SUFFIX)):
        return None
    digits = name[len(LOG_PREFIX):-len(LOG_SUFFIX)]
    if digits.isascii() and digits.isdigit():
        return int(digits)
    return None


def list_log_files(log_dir):
    """Rutas de las bitacoras de ``log_dir`` en orden NUMERICO.

    Orden numerico (no alfabetico): con orden alfabetico ``events_1000.log``
    quedaria antes que ``events_999.log``. Si la carpeta no existe o no se
    puede leer, devuelve una lista vacia (nunca lanza excepcion).
    """
    try:
        names = os.listdir(log_dir)
    except OSError:
        return []
    found = []
    for name in names:
        index = log_index(name)
        path = os.path.join(log_dir, name)
        if index is not None and os.path.isfile(path):
            found.append((index, path))
    found.sort()
    return [path for _, path in found]
