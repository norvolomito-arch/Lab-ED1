# ======================================================================
# ARCHIVO: tests/test_rubrica.py - pruebas de las PENALIZACIONES de la rubrica
# ======================================================================
# QUE PRUEBA: que no caigamos en las penalizaciones del laboratorio:
#   - Sin librerias prohibidas (statistics, numpy, pandas, matplotlib...).
#   - json solo para config.json.
#   - Nunca usar read() ni readlines() sobre la bitacora (cargarla entera).
#   - Memoria constante al leer aunque crezca la bitacora.
#   - Valores de referencia 8.1, 8.3, 8.4 y 8.5 correctos.
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Pruebas de cierre (Parte 13): penalizaciones de la rubrica.

- sin librerias prohibidas (analisis AST del codigo entregado)
- sin read()/readlines() sobre la bitacora
- lector en streaming: la memoria no crece con el tamano de la bitacora
- valores de validacion exactos (8.1, 8.3, 8.4, 8.5)
"""
# ast: permite leer el codigo de los archivos como un arbol y revisar que importan.
import ast
import os
import sys
import tempfile
import tracemalloc
import unittest

# Carpeta raiz del proyecto.
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from telemetry import iter_events
from game import statistics_engine as se

# Lista de librerias prohibidas y carpetas de codigo a revisar.
PROHIBIDOS = {"statistics", "numpy", "pandas", "scipy", "matplotlib",
              "plotly", "csv", "pickle"}
CARPETAS = ("game", "telemetry", "tools")


# Ayudante: lista todos los archivos .py del proyecto.
def _archivos_py():
    rutas = [os.path.join(ROOT, "main.py")]
    for carpeta in CARPETAS:
        for base, _dirs, nombres in os.walk(os.path.join(ROOT, carpeta)):
            for nombre in nombres:
                if nombre.endswith(".py"):
                    rutas.append(os.path.join(base, nombre))
    return rutas


# REVISION DEL CODIGO ENTREGADO.
class TestSinLibreriasProhibidas(unittest.TestCase):
    # Ningun archivo importa una libreria prohibida.
    def test_imports_prohibidos(self):
        for ruta in _archivos_py():
            with open(ruta, "r", encoding="utf-8") as f:
                arbol = ast.parse(f.read(), ruta)
            for nodo in ast.walk(arbol):
                if isinstance(nodo, ast.Import):
                    mods = [a.name.split(".")[0] for a in nodo.names]
                elif isinstance(nodo, ast.ImportFrom) and nodo.level == 0:
                    mods = [(nodo.module or "").split(".")[0]]
                    if nodo.module == "collections":
                        self.assertNotIn(
                            "Counter", [a.name for a in nodo.names], ruta)
                else:
                    continue
                self.assertFalse(set(mods) & PROHIBIDOS,
                                 "%s importa %s" % (ruta, mods))

    # json solo se usa en el archivo de ajustes.
    def test_json_solo_en_config(self):
        # json esta permitido solo para config.json
        for ruta in _archivos_py():
            with open(ruta, "r", encoding="utf-8") as f:
                if "import json" in f.read():
                    self.assertTrue(
                        ruta.endswith(("settings_screen.py", "main.py")),
                        "json fuera de configuracion: %s" % ruta)

    # Nadie llama a .read() ni .readlines() para leer la bitacora.
    def test_sin_read_ni_readlines(self):
        # busca llamadas .read() / .readlines() sin argumentos en el codigo
        for ruta in _archivos_py():
            with open(ruta, "r", encoding="utf-8") as f:
                arbol = ast.parse(f.read(), ruta)
            for nodo in ast.walk(arbol):
                if (isinstance(nodo, ast.Call)
                        and isinstance(nodo.func, ast.Attribute)
                        and nodo.func.attr in ("read", "readlines")
                        and not nodo.args):
                    self.fail("%s:%d usa .%s()" % (
                        ruta, nodo.lineno, nodo.func.attr))


# Ayudante: crea una bitacora minima con N sesiones.
def _generar(ruta_log, sesiones):
    """Bitacora minima valida con N sesiones (4 eventos por sesion)."""
    with open(ruta_log, "w", encoding="utf-8") as f:
        t = 1717000000.0
        for i in range(1, sesiones + 1):
            sid = "S%07d" % i
            t += 1
            f.write("%.3f|%s|SESSION_START|player=ana;difficulty=normal\n"
                    % (t, sid))
            f.write("%.3f|%s|ENEMY_KILL|type=slime;wave=1\n" % (t + .1, sid))
            f.write("%.3f|%s|PLAYER_DEATH|cause=slime;level=1\n"
                    % (t + .2, sid))
            f.write("%.3f|%s|SESSION_END|score=%d;level=1;duration=5;"
                    "result=death\n" % (t + .3, sid, 100 + i % 50))


# Ayudante: mide el pico de memoria al leer una bitacora.
def _pico_lectura(log_dir):
    tracemalloc.start()
    n = 0
    for _ev in iter_events(log_dir):
        n += 1
    pico = tracemalloc.get_traced_memory()[1]
    tracemalloc.stop()
    return n, pico


# PRUEBA DE MEMORIA.
class TestMemoriaConstante(unittest.TestCase):
    # Una bitacora 50 veces mas grande (100 000 eventos contra 2 000) no debe gastar
    # mucha mas memoria: el pico se mantiene bajo.
    def test_pico_no_crece_con_el_tamano(self):
        with tempfile.TemporaryDirectory() as d1, \
                tempfile.TemporaryDirectory() as d2:
            _generar(os.path.join(d1, "events_001.log"), 500)      # 2 000
            _generar(os.path.join(d2, "events_001.log"), 25000)    # 100 000
            n1, p1 = _pico_lectura(d1)
            n2, p2 = _pico_lectura(d2)
        self.assertEqual(n1, 2000)
        self.assertEqual(n2, 100000)
        # 50 veces mas eventos: el pico debe seguir en el mismo orden
        self.assertLess(p2, p1 * 3 + 64 * 1024)
        # y muy por debajo de lo que costaria guardar 100 000 dicts
        self.assertLess(p2, 512 * 1024)


# VALORES OFICIALES DEL LABORATORIO.
class TestValoresDeReferencia(unittest.TestCase):
    DATOS = [1200, 1500, 1500, 1800, 2100, 2400, 2400, 3000, 3600, 9000]

    # Medidas descriptivas.
    def test_8_1(self):
        r = se.basic_distribution(self.DATOS)
        self.assertEqual(r["n"], 10)
        self.assertEqual(r["sum"], 28500)
        self.assertAlmostEqual(r["mean"], 2850.00, 2)
        self.assertEqual((r["min"], r["max"], r["range"]), (1200, 9000, 7800))
        self.assertAlmostEqual(r["variance"], 5205000.00, 2)
        self.assertAlmostEqual(r["std"], 2281.45, 2)
        self.assertAlmostEqual(r["cv"], 80.05, 2)
        self.assertAlmostEqual(r["median"], 2250.00, 2)
        self.assertEqual((r["q1"], r["q3"], r["iqr"]), (1500, 3000, 1500))
        self.assertEqual(r["p90"], 3600)
        self.assertEqual((r["lower"], r["upper"]), (-750, 5250))
        self.assertEqual(r["outliers"], [9000])
        self.assertEqual(r["z_outliers"], [])

    # Tablas de frecuencia.
    def test_8_3_frecuencias(self):
        ses = {}
        reparto = (("slime", 412), ("arrow_trap", 298), ("boss", 190),
                   ("fall", 100))
        i = 0
        for causa, f in reparto:
            for _ in range(f):
                i += 1
                ses["S%d" % i] = {"cause": causa}
        tabla = se.frequency_table(ses, "cause")
        self.assertEqual([(t["value"], t["frequency"]) for t in tabla],
                         list(reparto))
        self.assertAlmostEqual(tabla[0]["relative"], 0.412, 6)
        self.assertAlmostEqual(tabla[-1]["cumulative"], 1.0, 6)
        self.assertEqual(se.mode_from_frequency(tabla), "slime")

    # Embudo de progresion.
    def test_8_4_embudo(self):
        # 500 sesiones: llegan a nivel 2/3/4/5 = 470/390/180/160
        llegan = (500, 470, 390, 180, 160)
        ses = {}
        i = 0
        for nivel in range(1, 6):
            exacto = llegan[nivel - 1] - (llegan[nivel] if nivel < 5 else 0)
            for _ in range(exacto):
                i += 1
                ses["S%d" % i] = {"max_level": nivel}
        filas = se.progression(ses)
        self.assertEqual([f["sessions"] for f in filas], list(llegan))
        self.assertAlmostEqual(filas[1]["abandonment"] * 100, 6.0, 1)
        self.assertAlmostEqual(filas[2]["abandonment"] * 100, 17.0, 0)
        self.assertAlmostEqual(filas[3]["abandonment"] * 100, 53.8, 1)
        self.assertAlmostEqual(filas[4]["abandonment"] * 100, 11.1, 1)

    # Correlacion de Pearson.
    def test_8_5_pearson(self):
        r = se.pearson([2, 4, 6, 8, 10, 12], [800, 1400, 1900, 2600, 3000, 3700])
        self.assertAlmostEqual(r, 0.99834, 5)


if __name__ == "__main__":
    unittest.main()
