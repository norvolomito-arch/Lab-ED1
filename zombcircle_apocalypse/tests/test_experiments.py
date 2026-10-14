# ======================================================================
# ARCHIVO: tests/test_experiments.py - pruebas de las herramientas de experimentos
# ======================================================================
# QUE PRUEBA: que los experimentos A, B y C y la libreria de graficas funcionen,
# usando tamanos diminutos para que las pruebas sean rapidas.
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Pruebas de las herramientas de experimentos A, B y C (con tamanos diminutos)."""
# Librerias para detectar pygame, rutas y pruebas.
import importlib.util
import os
import tempfile
import unittest

# Los experimentos que se prueban.
from tools.experiments import common, exp_a_buffer, exp_bc_read, plotlib
# Generador de eventos falsos.
from tools.gen_synthetic_log import build_events, generate

# Dice si pygame esta instalado (sin el no se pueden crear las graficas).
HAY_PYGAME = importlib.util.find_spec("pygame") is not None


# PRUEBAS DE LAS UTILIDADES.
class UtilidadesTests(unittest.TestCase):
    # La mediana funciona con cantidad par e impar.
    def test_mediana_con_sorted(self):
        self.assertEqual(common.mediana([3, 1, 2]), 2)
        self.assertEqual(common.mediana([4, 1, 3, 2]), 2.5)
        with self.assertRaises(ValueError):
            common.mediana([])

    # La lista de datos de la maquina trae todos los campos.
    def test_especificaciones_tienen_los_campos(self):
        campos = [c for c, _ in common.especificaciones()]
        self.assertEqual(campos, ["CPU", "Nucleos logicos", "RAM",
                                  "Tipo de disco", "Sistema operativo", "Python"])

    # Las marcas de los ejes son razonables.
    def test_ticks(self):
        marcas = plotlib.nice_ticks(0.0, 0.87)
        self.assertEqual(marcas[0], 0.0)
        self.assertGreaterEqual(marcas[-1], 0.87)
        self.assertEqual(plotlib.log_ticks(24.0, 65000.0), [10.0, 100.0, 1000.0, 10000.0, 100000.0])

    # build_events produce los mismos eventos que generate.
    def test_build_events_coincide_con_generate(self):
        eventos = build_events(500, seed=5)
        self.assertEqual(len(eventos), 500)
        self.assertEqual(eventos, build_events(500, seed=5))
        with tempfile.TemporaryDirectory() as tmp:
            info = generate(os.path.join(tmp, "x"), 500, seed=5)
            self.assertEqual(info["events"], 500)


# PRUEBAS DEL EXPERIMENTO A.
class ExperimentoATests(unittest.TestCase):
    # Se mide y se arma la tabla correctamente.
    def test_medicion_y_tabla(self):
        eventos = build_events(400, seed=1)
        tiempos = exp_a_buffer.ejecutar(eventos, buffers=(1, 10), reps=2)
        self.assertEqual(sorted(tiempos), [1, 10])
        self.assertTrue(all(len(v) == 2 and min(v) > 0 for v in tiempos.values()))
        filas = exp_a_buffer.resumir(tiempos)
        self.assertLessEqual(filas[0]["min"], filas[0]["mediana"])
        texto = exp_a_buffer.tabla_texto(filas, 400, tiempos, 2, 1)
        self.assertIn("Buffer | Min (s) | Mediana (s)", texto)
        self.assertIn("buffer 10:", texto)

    # No quedan carpetas temporales sin borrar.
    def test_no_deja_carpetas_temporales(self):
        with tempfile.TemporaryDirectory() as base:
            exp_a_buffer.medir_escritura(build_events(100, seed=1), 10, tmp_base=base)
            self.assertEqual(os.listdir(base), [])


# PRUEBAS DE LOS EXPERIMENTOS B y C.
class ExperimentoBCTests(unittest.TestCase):
    # La lista gasta mas memoria que la lectura perezosa.
    def test_medir_contraste_de_memoria(self):
        r = exp_bc_read.medir(3000, seed=1, buffer_size=25, reps=2, tmp_base=None)
        self.assertEqual(r["eventos"], 3000)
        self.assertGreater(r["eps"], 0)
        self.assertGreater(r["mem_lista"], 5 * r["mem_lazy"])

    # La tabla tiene exactamente las columnas esperadas y la version LaTeX
    # incluye la estructura de tabla.
    def test_tabla_con_columnas_exactas(self):
        r = exp_bc_read.medir(500, seed=1, buffer_size=10, reps=1, tmp_base=None)
        texto = exp_bc_read.tabla_texto([r], 10, 1, 1)
        enc = " | ".join(exp_bc_read.CABECERA)
        self.assertEqual(enc, "Eventos | Tamaño archivo | T. escritura | T. lectura | "
                              "Eventos/s | Mem. perezosa | Mem. lista")
        self.assertIn("Mem. lista", texto)
        tex = exp_bc_read.tabla_tex([r])
        self.assertIn("\\begin{tabular}{rrrrrrr}", tex)
        self.assertIn("\\label{tab:resumen}", tex)

    # El buffer leido de game/main.py es un entero positivo.
    def test_buffer_del_juego_es_entero_positivo(self):
        self.assertGreaterEqual(exp_bc_read.buffer_del_juego(), 1)


@unittest.skipUnless(HAY_PYGAME, "pygame no esta instalado")
# PRUEBAS DE LAS GRAFICAS.
class FigurasTests(unittest.TestCase):
    # Los archivos PNG de las graficas se crean.
    def test_los_png_se_crean(self):
        r = exp_bc_read.medir(400, seed=1, buffer_size=10, reps=1, tmp_base=None)
        with tempfile.TemporaryDirectory() as tmp:
            exp_bc_read.dibujar([r], tmp)
            exp_a_buffer.dibujar([{"buffer": 1, "min": 0.2, "mediana": 0.3},
                                  {"buffer": 10, "min": 0.1, "mediana": 0.2}],
                                 os.path.join(tmp, "exp_a.png"), 400)
            for nombre in ("exp_a.png", "exp_b.png", "exp_c.png"):
                self.assertGreater(os.path.getsize(os.path.join(tmp, nombre)), 1000)


if __name__ == "__main__":
    unittest.main()
