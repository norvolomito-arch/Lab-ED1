# ======================================================================
# ARCHIVO: tests/test_descriptive_stats.py - pruebas de las formulas de estadistica
# ======================================================================
# QUE PRUEBA: game/descriptive_stats.py con los datos de validacion del laboratorio
# (10 puntajes: 1200, 1500, ... 9000). Si los resultados coinciden con los valores
# oficiales (media 2850, mediana 2250, Q1 1500, Q3 3000, P90 3600...), las
# formulas estan bien.
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Pruebas con el conjunto de validacion del laboratorio (secciones 8.1 y 8.2)."""

# unittest: la herramienta de pruebas que trae Python.
import unittest

# Las funciones que vamos a probar.
from game.descriptive_stats import (
    RunningStats,
    atipicos_iqr,
    atipicos_z,
    cuartiles,
    iqr_y_limites,
    mediana,
    percentil_rango_mas_cercano,
    puntaje_z,
)

# Los 10 datos de referencia del laboratorio.
DATOS = [1200, 1500, 1500, 1800, 2100, 2400, 2400, 3000, 3600, 9000]


# Ayudante: mete todos los valores en un RunningStats y lo devuelve.
def acumular(valores):
    stats = RunningStats()
    for x in valores:
        stats.add(x)
    return stats


# PRUEBAS DE LAS MEDIDAS DE UNA PASADA (media, varianza, desviacion, CV, rango).
class DescriptivasUnaPasadaTests(unittest.TestCase):
    # Comprueba n, suma, media, minimo, maximo, rango, varianza, desviacion y CV
    # contra los valores oficiales del laboratorio (seccion 8.1).
    def test_valores_de_referencia_8_1(self):
        s = acumular(DATOS)
        self.assertEqual(s.n, 10)
        self.assertEqual(s.total, 28500)
        self.assertEqual(s.media, 2850.0)
        self.assertEqual((s.minimum, s.maximum), (1200, 9000))
        self.assertEqual(s.rango, 7800)
        self.assertAlmostEqual(s.varianza_muestral, 5205000.00, places=2)
        self.assertAlmostEqual(s.desviacion, 2281.45, places=2)
        self.assertAlmostEqual(s.cv_porcentaje, 80.05, places=2)

    # Sin datos, las medidas deben ser None (vacio), no dar error.
    def test_sin_datos_devuelve_none(self):
        s = RunningStats()
        self.assertIsNone(s.media)
        self.assertIsNone(s.varianza_muestral)
        self.assertIsNone(s.cv_porcentaje)

    # Con un solo dato hay media pero no varianza muestral (se divide entre n-1 = 0).
    def test_un_solo_dato_no_tiene_varianza_muestral(self):
        s = acumular([5])
        self.assertEqual(s.media, 5.0)
        self.assertIsNone(s.varianza_muestral)

    # Si todos los valores son iguales, la varianza es 0.
    def test_valores_iguales_dan_varianza_cero(self):
        s = acumular([7, 7, 7, 7])
        self.assertEqual(s.varianza_muestral, 0.0)


# PRUEBAS DE LAS MEDIDAS DE ORDEN (mediana, cuartiles, P90, atipicos).
class EstadisticasOrdenadasTests(unittest.TestCase):
    # Antes de cada prueba, se ordenan los datos.
    def setUp(self):
        self.ordenados = sorted(DATOS)

    # Mediana 2250, Q1 1500, Q3 3000, IQR 1500 y P90 3600 (seccion 8.2).
    def test_mediana_cuartiles_iqr_p90_8_2(self):
        self.assertEqual(mediana(self.ordenados), 2250.0)
        q1, q3 = cuartiles(self.ordenados)
        self.assertEqual((q1, q3), (1500.0, 3000.0))
        self.assertEqual(q3 - q1, 1500.0)
        self.assertEqual(percentil_rango_mas_cercano(self.ordenados, 90), 3600)

    # Limites de Tukey (-750 y 5250): el unico atipico es 9000.
    def test_limites_y_atipicos_por_iqr(self):
        _, _, _, inferior, superior = iqr_y_limites(self.ordenados)
        self.assertEqual((inferior, superior), (-750.0, 5250.0))
        self.assertEqual(atipicos_iqr(self.ordenados), [9000])

    # z de 9000 es 2.70, menor que 3, asi que por Z no hay atipicos (el dato
    # raro infla la desviacion y se 'esconde').
    def test_puntaje_z_y_atipicos_por_z(self):
        s = acumular(DATOS)
        self.assertAlmostEqual(puntaje_z(9000, s.media, s.desviacion), 2.70, places=2)
        self.assertEqual(atipicos_z(DATOS, 3.0), [])

    # Mediana con cantidad par, impar y lista vacia.
    def test_mediana_par_e_impar(self):
        self.assertEqual(mediana([4, 8]), 6.0)
        self.assertEqual(mediana([1, 5, 9]), 5.0)
        self.assertIsNone(mediana([]))

    # Con cantidad impar, el valor central no entra en ninguna mitad.
    def test_cuartiles_con_n_impar_excluyen_la_mediana(self):
        self.assertEqual(cuartiles([1, 2, 3, 4, 5]), (1.5, 4.5))


# Permite correr solo este archivo.
if __name__ == "__main__":
    unittest.main()