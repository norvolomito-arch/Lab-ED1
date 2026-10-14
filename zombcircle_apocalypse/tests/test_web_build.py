# ======================================================================
# ARCHIVO: tests/test_web_build.py - pruebas de preparacion para la web (pygbag)
# ======================================================================
# QUE PRUEBA: que el proyecto este listo para convertirse a pagina web:
#   - Hay una bitacora real pregenerada en logs/ y .gitignore no la excluye.
#   - La bitacora esta limpia y tiene 25 sesiones; el contador no choca con ids.
#   - Al arrancar se AGREGA a la bitacora, no se sobrescribe.
#   - Hay un solo audio y es .ogg; el main.py de la raiz cumple lo que pide pygbag.
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Pruebas de preparacion para pygbag (Parte 9): bitacora real y audio unico."""
# Librerias para revisar codigo, copiar carpetas y probar.
import ast
import os
import shutil
import tempfile
import unittest

# Lo necesario para leer y escribir bitacoras.
from telemetry import TelemetryWriter, QualityReport, iter_events
from telemetry.common import list_log_files

# Rutas del proyecto y de la carpeta logs.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")


# Ayudante: lee los patrones que .gitignore ignora.
def _ignored_patterns():
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


# Si todavia no hay bitacora real, la prueba se salta.
def _exigir_bitacora_real():
    """Salta la prueba si logs/ aun no tiene una bitacora real."""
    if not list_log_files(LOG_DIR):
        raise unittest.SkipTest("Aún no hay bitácora real")


# PRUEBAS DE LA VERSION WEB.
class TestWebBuild(unittest.TestCase):
    # Existe una bitacora pregenerada.
    def test_hay_bitacora_pregenerada(self):
        _exigir_bitacora_real()
        self.assertTrue(list_log_files(LOG_DIR))

    # .gitignore no excluye los logs (si no, no viajarian al navegador).
    def test_gitignore_no_excluye_la_bitacora(self):
        for pat in _ignored_patterns():
            self.assertNotIn(pat.rstrip("/"), ("logs", "*.log", "events_*.log",
                                               "session_counter.txt"))

    # La bitacora real no tiene lineas corruptas y tiene 25 sesiones completas.
    def test_bitacora_real_limpia_y_con_25_sesiones(self):
        _exigir_bitacora_real()
        report = QualityReport()
        ends = set()
        for ev in iter_events(LOG_DIR, report):
            if ev["event_type"] == "SESSION_END":
                ends.add(ev["session_id"])
        self.assertEqual(report.corrupt, 0)
        self.assertGreaterEqual(len(ends), 25)

    # El contador de sesiones continua despues del ultimo id ya escrito.
    def test_contador_no_choca_con_ids_de_la_bitacora(self):
        # En web el contador viaja en el build; si fuera menor que el id
        # maximo de la bitacora, una partida nueva repetiria un session_id.
        _exigir_bitacora_real()
        mayor = 0
        for ev in iter_events(LOG_DIR):
            mayor = max(mayor, int(ev["session_id"][1:]))
        with open(os.path.join(ROOT, "session_counter.txt"), encoding="utf-8") as f:
            contador = int(f.readline())
        self.assertGreaterEqual(contador, mayor)

    # Al abrir el escritor sobre los logs existentes se agrega sin borrar.
    def test_arranque_web_agrega_sin_sobrescribir(self):
        _exigir_bitacora_real()
        tmp = tempfile.mkdtemp()
        try:
            copia = os.path.join(tmp, "logs")
            shutil.copytree(LOG_DIR, copia)
            ruta = os.path.join(copia, "events_001.log")
            with open(ruta, "rb") as f:
                antes = f.read()
            with TelemetryWriter(copia, 25, 512 * 1024) as w:
                w.log("SESSION_START", "S9999", player="web", difficulty="easy")
            with open(ruta, "rb") as f:
                despues = f.read()
            self.assertTrue(despues.startswith(antes))
            self.assertGreater(len(despues), len(antes))
        finally:
            shutil.rmtree(tmp)

    def test_prepare_web_renombra_bitacoras_para_pygbag(self):
        # pygbag descarta los archivos ".log"; en el build deben ir como .txt
        # y seguir siendo legibles por el lector.
        _exigir_bitacora_real()
        import sys
        sys.path.insert(0, os.path.join(ROOT, "tools"))
        import prepare_web
        tmp = tempfile.mkdtemp()
        try:
            destino, nombres = prepare_web.prepare(os.path.join(tmp, "stage"))
            self.assertTrue(nombres)
            logs = os.path.join(destino, "logs")
            self.assertFalse([n for n in os.listdir(logs) if n.endswith(".log")])
            report = QualityReport()
            total = sum(1 for _ in iter_events(logs, report))
            self.assertGreater(total, 0)
            self.assertEqual(report.corrupt, 0)
        finally:
            shutil.rmtree(tmp)

    def test_un_solo_audio(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "game", "audio-pygbag.py")))
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            self.assertNotIn("audio-pygbag", f.read())

    # En la web solo se acepta .ogg.
    def test_audio_web_solo_ogg(self):
        try:
            from game import audio
        except ImportError:
            self.skipTest("pygame no instalado")
        self.assertEqual(audio.MUSIC_FILENAMES_WEB, ("theme.ogg",))
        self.assertIn("theme.ogg", audio.MUSIC_FILENAMES_LOCAL)

    # El main.py de la raiz importa pygame y su ultima instruccion es
    # asyncio.run(main()), como exige pygbag.
    def test_main_raiz_cumple_pygbag(self):
        with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        importa_pygame = any(isinstance(n, ast.Import) and
                             any(a.name == "pygame" for a in n.names)
                             for n in tree.body)
        ultima = ast.unparse(tree.body[-1])
        self.assertTrue(importa_pygame)
        self.assertEqual(ultima, "asyncio.run(main())")

    # Los archivos de game/ y telemetry/ no importan librerias que dan problemas
    # en el navegador (threading, socket, subprocess...).
    def test_sin_librerias_problematicas_en_el_juego(self):
        prohibidos = {"threading", "socket", "subprocess", "multiprocessing",
                      "tracemalloc", "platform"}
        for carpeta in ("game", "telemetry"):
            for nombre in os.listdir(os.path.join(ROOT, carpeta)):
                if not nombre.endswith(".py"):
                    continue
                with open(os.path.join(ROOT, carpeta, nombre), encoding="utf-8") as f:
                    tree = ast.parse(f.read())
                for n in ast.walk(tree):
                    if isinstance(n, ast.Import):
                        mods = {a.name.split(".")[0] for a in n.names}
                    elif isinstance(n, ast.ImportFrom) and n.module:
                        mods = {n.module.split(".")[0]}
                    else:
                        continue
                    self.assertFalse(mods & prohibidos, "%s/%s" % (carpeta, nombre))


if __name__ == "__main__":
    unittest.main()
