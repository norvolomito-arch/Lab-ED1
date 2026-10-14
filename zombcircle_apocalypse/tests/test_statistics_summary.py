# ======================================================================
# ARCHIVO: tests/test_statistics_summary.py - pruebas del motor de analisis
# ======================================================================
# QUE PRUEBA: game/statistics_engine.py: que 'basic_distribution' reproduzca los
# valores de referencia, que la comparacion por dificultad funcione y que la
# correlacion de Pearson en una pasada de el valor oficial (r = 0.99834).
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""basic_distribution debe reproducir los valores de referencia (8.1 y 8.2)."""
 
# Herramienta de pruebas.
import unittest
 
# Lo que vamos a probar.
from game.statistics_engine import (Correlation, basic_distribution, correlation_data,
                                    difficulty_comparison)
 
# Los 10 datos de referencia del laboratorio.
DATOS = [1200, 1500, 1500, 1800, 2100, 2400, 2400, 3000, 3600, 9000]
 
 
# PRUEBAS DEL RESUMEN ESTADISTICO.
class ResumenDeReferenciaTests(unittest.TestCase):
    # Antes de cada prueba se calcula el resumen de los datos.
    def setUp(self):
        self.r = basic_distribution(DATOS)
 
    # Medidas descriptivas contra los valores oficiales.
    def test_descriptivas_8_1(self):
        r = self.r
        self.assertEqual(r["n"], 10)
        self.assertEqual(r["sum"], 28500)
        self.assertEqual(r["mean"], 2850.0)
        self.assertEqual((r["min"], r["max"]), (1200, 9000))
        self.assertEqual(r["range"], 7800)
        self.assertAlmostEqual(r["variance"], 5205000.00, places=2)
        self.assertAlmostEqual(r["std"], 2281.45, places=2)
        self.assertAlmostEqual(r["cv"], 80.05, places=2)
 
    # Mediana, cuartiles, P90, limites y atipicos contra los valores oficiales.
    def test_orden_8_2(self):
        r = self.r
        self.assertEqual(r["median"], 2250.0)
        self.assertEqual((r["q1"], r["q3"], r["iqr"]), (1500.0, 3000.0, 1500.0))
        self.assertEqual(r["p90"], 3600)
        self.assertEqual((r["lower"], r["upper"]), (-750.0, 5250.0))
        self.assertEqual(r["outliers"], [9000.0])
        self.assertEqual(r["z_outliers"], [])
 
    # Lista vacia: todo en cero, sin error (para que la pantalla no falle).
    def test_lista_vacia_no_rompe_la_pantalla(self):
        r = basic_distribution([])
        self.assertEqual(r["n"], 0)
        self.assertEqual(r["mean"], 0.0)
        self.assertEqual(r["outliers"], [])
 
    # Un solo valor: todas las medidas valen ese valor y la desviacion 0.
    def test_un_solo_valor(self):
        r = basic_distribution([5])
        self.assertEqual((r["mean"], r["median"], r["q1"], r["q3"]), (5.0, 5.0, 5.0, 5.0))
        self.assertEqual(r["std"], 0.0)
 
    # El resumen debe incluir todas las claves que la pantalla necesita.
    def test_claves_que_usa_la_pantalla(self):
        for clave in ("n", "mean", "median", "std", "min", "max", "p90",
                      "iqr", "q1", "q3", "lower", "upper", "outliers"):
            self.assertIn(clave, self.r)
 

# PRUEBAS DE LA COMPARACION POR DIFICULTAD.
class ComparacionDificultadTests(unittest.TestCase):
    # Cantidades y promedios por dificultad, y diferencia hard-easy (-1000 = -50%).
    def test_incluye_las_tres_dificultades(self):
        ses = {
            "S1": {"score": 1000, "difficulty": "easy"},
            "S2": {"score": 3000, "difficulty": "easy"},
            "S3": {"score": 1500, "difficulty": "normal"},
            "S4": {"score": 500, "difficulty": "hard"},
            "S5": {"score": 1500, "difficulty": "hard"},
        }
        r = difficulty_comparison(ses)
        self.assertEqual([r[d]["n"] for d in ("easy", "normal", "hard")],
                         [2, 1, 2])
        self.assertEqual(r["easy"]["mean"], 2000)
        self.assertEqual(r["normal"]["mean"], 1500)
        self.assertEqual(r["hard"]["mean"], 1000)
        self.assertEqual(r["difference"], -1000)
        self.assertAlmostEqual(r["percentage_vs_easy"], -50.0)

    # Una dificultad sin partidas no rompe el calculo.
    def test_grupo_vacio_no_rompe(self):
        r = difficulty_comparison({"S1": {"score": 10, "difficulty": "easy"}})
        self.assertEqual(r["normal"]["n"], 0)
        self.assertEqual(r["hard"]["n"], 0)

# PRUEBAS DE LA CORRELACION DE PEARSON.
class PearsonUnaPasadaTests(unittest.TestCase):
    # Datos de ejemplo del laboratorio: tiempo (minutos) y puntaje.
    TIEMPO = [2, 4, 6, 8, 10, 12]
    PUNTAJE = [800, 1400, 1900, 2600, 3000, 3700]

    # Las 6 sumas acumuladas y r = 0.99834.
    def test_sumas_y_r_de_referencia_8_5(self):
        c = Correlation()
        for x, y in zip(self.TIEMPO, self.PUNTAJE):
            c.add(x, y)
        self.assertEqual((c.n, c.sx, c.sy, c.sxy), (6, 42, 13400, 113800))
        self.assertAlmostEqual(c.r(), 0.99834, places=5)

    # La funcion que usa la pantalla da el mismo r.
    def test_correlation_data_usa_las_sumas(self):
        ses = {"S%d" % i: {"duration": x, "score": y}
               for i, (x, y) in enumerate(zip(self.TIEMPO, self.PUNTAJE))}
        xs, ys, r = correlation_data(ses)
        self.assertEqual(len(xs), 6)
        self.assertAlmostEqual(r, 0.99834, places=5)

    # Sin datos o sin variacion, r = 0.
    def test_casos_borde(self):
        self.assertEqual(Correlation().r(), 0.0)
        c = Correlation()
        for _ in range(3):
            c.add(5, 7)
        self.assertEqual(c.r(), 0.0)      # varianza cero



# Permite correr solo este archivo.
if __name__ == "__main__":
    unittest.main()
