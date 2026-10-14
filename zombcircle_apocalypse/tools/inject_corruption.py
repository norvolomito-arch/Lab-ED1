# ======================================================================
# ARCHIVO: tools/inject_corruption.py - fabrica una bitacora con lineas danadas
# ======================================================================
# QUE ES: copia las bitacoras reales a otra carpeta y agrega un archivo extra con
# lineas corruptas a proposito. Sirve para DEMOSTRAR que el lector no se cae y que
# el reporte de calidad cuenta bien las lineas malas.
# COMO SE USA:  python tools/inject_corruption.py ORIGEN DESTINO
# ======================================================================

"""Copy event logs and add corrupt records in a new rotated file."""

# os: rutas y carpetas.
import os
# sys: argumentos y codigo de salida.
import sys

# Raiz del proyecto en la ruta de Python.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Funciones para listar y nombrar archivos de bitacora.
from telemetry.common import list_log_files, log_filename, log_index

# Cuatro lineas malas de ejemplo: texto cualquiera, parametro sin '=',
# numero invalido y una linea en blanco.
CORRUPT_LINES = (
    b"this is not a valid event line\n",
    b"1.0|S-CORRUPT|CUSTOM|missing_equals\n",
    b"1.0|S-CORRUPT|SESSION_END|score=not-a-number\n",
    b"   \n",
)


# Copia los logs sin cambiarlos y luego crea un archivo nuevo con las lineas danadas.
def copy_logs_with_corruption(source_dir, destination_dir):
    """Copy source logs unchanged, then write corrupt examples separately."""
    # Convertimos las carpetas a rutas completas y comprobamos que origen y
    # destino sean distintos (para no danar los datos originales).
    source_path = os.path.realpath(os.path.abspath(source_dir))
    destination_path = os.path.realpath(os.path.abspath(destination_dir))
    if source_path == destination_path:
        raise ValueError("La carpeta de destino debe ser distinta a la original")

    # Debe haber bitacoras en el origen y el destino no debe tener ya bitacoras.
    source_files = list_log_files(source_path)
    if not source_files:
        raise ValueError("No se encontraron archivos events_NNN.log en el origen")

    # Creamos el destino si hace falta.
    os.makedirs(destination_path, exist_ok=True)
    if list_log_files(destination_path):
        raise ValueError("La carpeta de destino ya contiene archivos de bitacora")

    # Copiamos cada archivo linea por linea, tal cual.
    for source_file_path in source_files:
        destination_file_path = os.path.join(
            destination_path, os.path.basename(source_file_path))
        with open(source_file_path, "rb") as source_file:
            with open(destination_file_path, "wb") as destination_file:
                for line in source_file:
                    destination_file.write(line)

    # El archivo corrupto toma el siguiente numero (ej. events_004.log).
    last_index = log_index(source_files[-1])
    corrupt_filename = log_filename(last_index + 1)
    corrupt_file_path = os.path.join(destination_path, corrupt_filename)
    # Escribimos en el, una por una, las lineas danadas.
    with open(corrupt_file_path, "wb") as corrupt_file:
        for line in CORRUPT_LINES:
            corrupt_file.write(line)

    # Devolvemos cuantos archivos se copiaron, el nombre del archivo malo y cuantas lineas malas hay.
    return len(source_files), corrupt_filename, len(CORRUPT_LINES)


# Revisa los argumentos de la terminal y ejecuta la copia. Devuelve 0 si salio
# bien, 1 si hubo error y 2 si se usaron mal los argumentos.
def main(arguments):
    """Validate command arguments and run the corruption-copy operation."""
    if len(arguments) != 2:
        print("Uso: python tools/inject_corruption.py ORIGEN DESTINO")
        return 2

    try:
        copied_count, corrupt_filename, corrupt_count = copy_logs_with_corruption(
            arguments[0], arguments[1])
    except (OSError, ValueError) as error:
        print("Error: %s" % error)
        return 1

    print("Archivos copiados: %s" % format(copied_count, ","))
    print("Destino: %s" % os.path.abspath(arguments[1]))
    print("Lineas corruptas agregadas en %s: %s" % (
        corrupt_filename, corrupt_count))
    return 0


# Al ejecutarlo directamente, se corre main() con lo escrito en la terminal.
if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))