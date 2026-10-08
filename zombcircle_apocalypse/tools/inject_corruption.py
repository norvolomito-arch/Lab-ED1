"""Copy event logs and add corrupt records in a new rotated file."""

import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from telemetry.common import list_log_files, log_filename, log_index

CORRUPT_LINES = (
    b"this is not a valid event line\n",
    b"1.0|S-CORRUPT|CUSTOM|missing_equals\n",
    b"1.0|S-CORRUPT|SESSION_END|score=not-a-number\n",
    b"   \n",
)


def copy_logs_with_corruption(source_dir, destination_dir):
    """Copy source logs unchanged, then write corrupt examples separately."""
    source_path = os.path.realpath(os.path.abspath(source_dir))
    destination_path = os.path.realpath(os.path.abspath(destination_dir))
    if source_path == destination_path:
        raise ValueError("La carpeta de destino debe ser distinta a la original")

    source_files = list_log_files(source_path)
    if not source_files:
        raise ValueError("No se encontraron archivos events_NNN.log en el origen")

    os.makedirs(destination_path, exist_ok=True)
    if list_log_files(destination_path):
        raise ValueError("La carpeta de destino ya contiene archivos de bitacora")

    for source_file_path in source_files:
        destination_file_path = os.path.join(
            destination_path, os.path.basename(source_file_path))
        with open(source_file_path, "rb") as source_file:
            with open(destination_file_path, "wb") as destination_file:
                for line in source_file:
                    destination_file.write(line)

    last_index = log_index(source_files[-1])
    corrupt_filename = log_filename(last_index + 1)
    corrupt_file_path = os.path.join(destination_path, corrupt_filename)
    with open(corrupt_file_path, "wb") as corrupt_file:
        for line in CORRUPT_LINES:
            corrupt_file.write(line)

    return len(source_files), corrupt_filename, len(CORRUPT_LINES)


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


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))