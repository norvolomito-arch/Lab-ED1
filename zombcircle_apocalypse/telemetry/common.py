# ======================================================================
# ARCHIVO: telemetry/common.py - reglas compartidas por el escritor y el lector
# ======================================================================
# QUE ES: contiene cosas que el escritor y el lector deben entender IGUAL:
#   1) 'Escapar' texto: si un nombre trae simbolos que tienen un significado
#      especial en la bitacora (| ; =) se reemplazan por codigos (%7C %3B %3D)
#      para no romper el formato de la linea. Despues se pueden revertir.
#   2) Nombres de archivo: events_001.log, events_002.log... y como ordenarlos.
# ======================================================================

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
# os: para manejar nombres de archivo y listar carpetas.
import os

# Todos los archivos de bitacora empiezan por 'events_' y terminan en '.log'.
LOG_PREFIX = "events_"
LOG_SUFFIX = ".log"
# pygbag descarta los archivos ".log" al empaquetar (SKIP_EXT en su
# filtering.py), asi que en el build web las bitacoras viajan como
# ``events_NNN.txt`` (ver tools/prepare_web.py). El lector acepta ambas.
LOG_SUFFIXES = (LOG_SUFFIX, ".txt")

# Orden importa: "%" va primero al escapar para no re-escapar los codigos
# que se acaban de generar; al des-escapar se recorre al reves.
_ESCAPES = (("%", "%25"), ("|", "%7C"), (";", "%3B"), ("=", "%3D"),
            ("\n", "%0A"), ("\r", "%0D"))


# ESCAPAR: convierte cualquier valor en texto seguro (sin | ; = ni saltos de linea).
def escape(value):
    """Devuelve ``str(value)`` sin delimitadores ni saltos de linea."""
    # Pasamos a texto y aplicamos cada reemplazo de la tabla.
    text = str(value)
    for char, code in _ESCAPES:
        text = text.replace(char, code)
    return text


# DES-ESCAPAR: lo contrario de escape; devuelve el texto original
# (se aplica la tabla al reves).
def unescape(text):
    """Inversa exacta de :func:`escape`."""
    for char, code in reversed(_ESCAPES):
        text = text.replace(code, char)
    return text


# Arma el nombre del archivo numero N con 3 digitos: 1 -> events_001.log.
def log_filename(index):
    """Nombre del archivo numero ``index``: 1 -> ``events_001.log``."""
    return "%s%03d%s" % (LOG_PREFIX, index, LOG_SUFFIX)


# Del nombre de un archivo saca su numero (events_007.log -> 7).
# Si el nombre no sigue el patron, devuelve None.
def log_index(name):
    """Numero N de un archivo ``events_N.log``; None si no sigue el patron."""
    # Nos quedamos solo con el nombre, sin la carpeta.
    name = os.path.basename(name)
    suffix = next((s for s in LOG_SUFFIXES if name.endswith(s)), None)
    if suffix is None or not name.startswith(LOG_PREFIX):
        return None
    digits = name[len(LOG_PREFIX):-len(suffix)]
    if digits.isascii() and digits.isdigit():
        return int(digits)
    return None


# Lista las bitacoras de una carpeta en orden NUMERICO (no alfabetico,
# asi events_1000 va despues de events_999). Si la carpeta no existe,
# devuelve lista vacia.
def list_log_files(log_dir):
    """Rutas de las bitacoras de ``log_dir`` en orden NUMERICO.

    Orden numerico (no alfabetico): con orden alfabetico ``events_1000.log``
    quedaria antes que ``events_999.log``. Si la carpeta no existe o no se
    puede leer, devuelve una lista vacia (nunca lanza excepcion).
    """
    # Intentamos ver que hay dentro de la carpeta.
    try:
        names = os.listdir(log_dir)
    except OSError:
        return []
    # Guardamos (numero, ruta) de cada archivo valido y luego ordenamos.
    found = []
    for name in names:
        index = log_index(name)
        path = os.path.join(log_dir, name)
        if index is not None and os.path.isfile(path):
            found.append((index, path))
    found.sort()
    return [path for _, path in found]
