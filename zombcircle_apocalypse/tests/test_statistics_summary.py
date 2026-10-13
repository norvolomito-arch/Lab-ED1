"""basic_distribution debe reproducir los valores de referencia (8.1 y 8.2)."""
 
import unittest
 
from game.statistics_engine import basic_distribution, difficulty_comparison
 
DATOS = [1200, 1500, 1500, 1800, 2100, 2400, 2400, 3000, 3600, 9000]
 
 
class ResumenDeReferenciaTests(unittest.TestCase):
    def setUp(self):
        self.r = basic_distribution(DATOS)
 
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
 
    def test_orden_8_2(self):
        r = self.r
        self.assertEqual(r["median"], 2250.0)
        self.assertEqual((r["q1"], r["q3"], r["iqr"]), (1500.0, 3000.0, 1500.0))
        self.assertEqual(r["p90"], 3600)
        self.assertEqual((r["lower"], r["upper"]), (-750.0, 5250.0))
        self.assertEqual(r["outliers"], [9000.0])
        self.assertEqual(r["z_outliers"], [])
 
    def test_lista_vacia_no_rompe_la_pantalla(self):
        r = basic_distribution([])
        self.assertEqual(r["n"], 0)
        self.assertEqual(r["mean"], 0.0)
        self.assertEqual(r["outliers"], [])
 
    def test_un_solo_valor(self):
        r = basic_distribution([5])
        self.assertEqual((r["mean"], r["median"], r["q1"], r["q3"]), (5.0, 5.0, 5.0, 5.0))
        self.assertEqual(r["std"], 0.0)
 
    def test_claves_que_usa_la_pantalla(self):
        for clave in ("n", "mean", "median", "std", "min", "max", "p90",
                      "iqr", "q1", "q3", "lower", "upper", "outliers"):
            self.assertIn(clave, self.r)
 

class ComparacionDificultadTests(unittest.TestCase):
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

    def test_grupo_vacio_no_rompe(self):
        r = difficulty_comparison({"S1": {"score": 10, "difficulty": "easy"}})
        self.assertEqual(r["normal"]["n"], 0)
        self.assertEqual(r["hard"]["n"], 0)


if __name__ == "__main__":
    unittest.main()
 