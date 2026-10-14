"""Prepara una copia del proyecto para empaquetarla con pygbag.

Problema: pygbag ignora los archivos con extension ``.log`` (SKIP_EXT en
pygbag/filtering.py), por lo que ``logs/events_NNN.log`` no llega al build
y la pantalla Statistics en el navegador aparece sin datos.

Solucion: copiar el proyecto a una carpeta de preparacion y renombrar alli
``events_NNN.log`` -> ``events_NNN.txt`` (el lector acepta ambas extensiones).
El repositorio original no se modifica.

Uso (desde la raiz del repo):

    python tools/prepare_web.py [carpeta_destino]     # por defecto: web_stage
    python -m pygbag --build web_stage
    python -m http.server 8000 --directory web_stage/build/web
"""
import os
import shutil
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from telemetry.common import list_log_files  # noqa: E402

EXCLUDE = shutil.ignore_patterns("__pycache__", "*.pyc", "build", ".git",
                                 "web_stage", "logs_corruptos", "results",
                                 "tests", "tools")


def prepare(dest):
    dest = os.path.abspath(dest)
    if dest == ROOT or ROOT.startswith(dest + os.sep):
        raise ValueError("destino invalido: %s" % dest)
    if os.path.isdir(dest):
        shutil.rmtree(dest)
    shutil.copytree(ROOT, dest, ignore=EXCLUDE)
    logs = os.path.join(dest, "logs")
    renamed = []
    for path in list_log_files(logs):
        if path.endswith(".log"):
            new = path[:-len(".log")] + ".txt"
            os.rename(path, new)
            renamed.append(os.path.basename(new))
    return dest, renamed


if __name__ == "__main__":
    target = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, "web_stage")
    out, names = prepare(target)
    print("Carpeta lista: %s" % out)
    print("Bitacoras incluidas: %s" % (", ".join(names) or "NINGUNA"))
    print("Siguiente: python -m pygbag --build %s" % out)
