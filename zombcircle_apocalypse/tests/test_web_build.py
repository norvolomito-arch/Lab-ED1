"""Pruebas de preparacion para pygbag (Parte 9): bitacora real y audio unico."""
import ast
import os
import shutil
import tempfile
import unittest

from telemetry import TelemetryWriter, QualityReport, iter_events
from telemetry.common import list_log_files

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG_DIR = os.path.join(ROOT, "logs")


def _ignored_patterns():
    with open(os.path.join(ROOT, ".gitignore"), encoding="utf-8") as f:
        return [l.strip() for l in f if l.strip() and not l.startswith("#")]


def _exigir_bitacora_real():
    """Salta la prueba si logs/ aun no tiene una bitacora real."""
    if not list_log_files(LOG_DIR):
        raise unittest.SkipTest("Aún no hay bitácora real")


class TestWebBuild(unittest.TestCase):
    def test_hay_bitacora_pregenerada(self):
        _exigir_bitacora_real()
        self.assertTrue(list_log_files(LOG_DIR))

    def test_gitignore_no_excluye_la_bitacora(self):
        for pat in _ignored_patterns():
            self.assertNotIn(pat.rstrip("/"), ("logs", "*.log", "events_*.log",
                                               "session_counter.txt"))

    def test_bitacora_real_limpia_y_con_25_sesiones(self):
        _exigir_bitacora_real()
        report = QualityReport()
        ends = set()
        for ev in iter_events(LOG_DIR, report):
            if ev["event_type"] == "SESSION_END":
                ends.add(ev["session_id"])
        self.assertEqual(report.corrupt, 0)
        self.assertGreaterEqual(len(ends), 25)

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

    def test_un_solo_audio(self):
        self.assertFalse(os.path.exists(os.path.join(ROOT, "game", "audio-pygbag.py")))
        with open(os.path.join(ROOT, "README.md"), encoding="utf-8") as f:
            self.assertNotIn("audio-pygbag", f.read())

    def test_audio_web_solo_ogg(self):
        try:
            from game import audio
        except ImportError:
            self.skipTest("pygame no instalado")
        self.assertEqual(audio.MUSIC_FILENAMES_WEB, ("theme.ogg",))
        self.assertIn("theme.ogg", audio.MUSIC_FILENAMES_LOCAL)

    def test_main_raiz_cumple_pygbag(self):
        with open(os.path.join(ROOT, "main.py"), encoding="utf-8") as f:
            tree = ast.parse(f.read())
        importa_pygame = any(isinstance(n, ast.Import) and
                             any(a.name == "pygame" for a in n.names)
                             for n in tree.body)
        ultima = ast.unparse(tree.body[-1])
        self.assertTrue(importa_pygame)
        self.assertEqual(ultima, "asyncio.run(main())")

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
