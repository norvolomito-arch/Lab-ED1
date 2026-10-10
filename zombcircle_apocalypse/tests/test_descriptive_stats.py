"""Pruebas con el conjunto de validacion del laboratorio (secciones 8.1 y 8.2)."""

import unittest

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

DATOS = [1200, 1500, 1500, 1800, 2100, 2400, 2400, 3000, 3600, 9000]


def acumular(valores):
    stats = RunningStats()
    for x in valores:
        stats.add(x)
    return stats


class DescriptivasUnaPasadaTests(unittest.TestCase):
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

    def test_sin_datos_devuelve_none(self):
        s = RunningStats()
        self.assertIsNone(s.media)
        self.assertIsNone(s.varianza_muestral)
        self.assertIsNone(s.cv_porcentaje)

    def test_un_solo_dato_no_tiene_varianza_muestral(self):
        s = acumular([5])
        self.assertEqual(s.media, 5.0)
        self.assertIsNone(s.varianza_muestral)

    def test_valores_iguales_dan_varianza_cero(self):
        s = acumular([7, 7, 7, 7])
        self.assertEqual(s.varianza_muestral, 0.0)


class EstadisticasOrdenadasTests(unittest.TestCase):
    def setUp(self):
        self.ordenados = sorted(DATOS)

    def test_mediana_cuartiles_iqr_p90_8_2(self):
        self.assertEqual(mediana(self.ordenados), 2250.0)
        q1, q3 = cuartiles(self.ordenados)
        self.assertEqual((q1, q3), (1500.0, 3000.0))
        self.assertEqual(q3 - q1, 1500.0)
        self.assertEqual(percentil_rango_mas_cercano(self.ordenados, 90), 3600)

    def test_limites_y_atipicos_por_iqr(self):
        _, _, _, inferior, superior = iqr_y_limites(self.ordenados)
        self.assertEqual((inferior, superior), (-750.0, 5250.0))
        self.assertEqual(atipicos_iqr(self.ordenados), [9000])

    def test_puntaje_z_y_atipicos_por_z(self):
        s = acumular(DATOS)
        self.assertAlmostEqual(puntaje_z(9000, s.media, s.desviacion), 2.70, places=2)
        self.assertEqual(atipicos_z(DATOS, 3.0), [])

    def test_mediana_par_e_impar(self):
        self.assertEqual(mediana([4, 8]), 6.0)
        self.assertEqual(mediana([1, 5, 9]), 5.0)
        self.assertIsNone(mediana([]))

    def test_cuartiles_con_n_impar_excluyen_la_mediana(self):
        self.assertEqual(cuartiles([1, 2, 3, 4, 5]), (1.5, 4.5))


if __name__ == "__main__":
    unittest.main()