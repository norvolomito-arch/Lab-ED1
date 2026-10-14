# ======================================================================
# ARCHIVO: tests/test_synthetic_generator.py - pruebas del generador de bitacoras falsas
# ======================================================================
# QUE PRUEBA: tools/gen_synthetic_log.py: que con la misma semilla genere los mismos
# bytes, que cuente exacto, rote archivos, inserte lineas corruptas detectables y
# que las sesiones sean coherentes (hard = mas dano y menos puntaje que easy).
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Pruebas del generador de bitacoras sinteticas (tools/gen_synthetic_log.py)."""
# Librerias para capturar salida, azar, rutas y pruebas.
import contextlib
import io
import os
import random
import tempfile
import unittest

# Lector y reporte (para verificar lo generado).
from telemetry import QualityReport, iter_events, parse_line
from telemetry.common import list_log_files
# El generador que se prueba.
from tools import gen_synthetic_log as gen


# Ayudante: lee todos los archivos de una bitacora como bytes.
def leer_bytes(carpeta):
    """Lista de (nombre, bytes) de todos los archivos de la bitacora."""
    salida = []
    for ruta in list_log_files(carpeta):
        with open(ruta, "rb") as f:
            salida.append((os.path.basename(ruta), f.read()))
    return salida


# PRUEBAS DEL GENERADOR.
class SyntheticGeneratorTests(unittest.TestCase):
    # Antes de cada prueba: carpeta temporal.
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    # Despues: se borra.
    def tearDown(self):
        self.tmp.cleanup()

    # Ayudante: crea una subcarpeta con nombre.
    def carpeta(self, nombre):
        return os.path.join(self.tmp.name, nombre)

    # Ayudante: calcula el reporte de calidad de una carpeta.
    def calidad(self, carpeta):
        reporte = QualityReport()
        eventos = list(iter_events(carpeta, report=reporte))
        return reporte, eventos

    # Misma semilla = mismos bytes.
    def test_mismo_seed_mismos_bytes(self):
        a, b, c = self.carpeta("a"), self.carpeta("b"), self.carpeta("c")
        gen.generate(a, 3000, seed=7, max_bytes=20000, corrupt_rate=0.03)
        gen.generate(b, 3000, seed=7, max_bytes=20000, corrupt_rate=0.03)
        gen.generate(c, 3000, seed=8, max_bytes=20000, corrupt_rate=0.03)
        self.assertEqual(leer_bytes(a), leer_bytes(b))
        self.assertNotEqual(leer_bytes(a), leer_bytes(c))

    # Sin corrupcion pedida, cero lineas corruptas.
    def test_sin_corrupcion_cero_lineas_corruptas(self):
        d = self.carpeta("limpia")
        info = gen.generate(d, 4000, seed=1, corrupt_rate=0.0)
        reporte, _ = self.calidad(d)
        self.assertEqual(reporte.corrupt, 0)
        self.assertEqual(reporte.valid, 4000)
        self.assertEqual(reporte.lines_read, info["lines"])
        self.assertEqual(reporte.incomplete_sessions, 0)

    # Se escribe exactamente la cantidad de eventos pedida.
    def test_conteo_exacto_de_eventos(self):
        for n in (2, 3, 4, 5, 7, 40, 100, 1234):
            d = self.carpeta("n%d" % n)
            info = gen.generate(d, n, seed=3)
            reporte, _ = self.calidad(d)
            self.assertEqual(info["events"], n, n)
            self.assertEqual(reporte.valid, n, n)
            self.assertEqual(reporte.incomplete_sessions, 0, n)

    # Con un limite pequeno se crean varios archivos.
    def test_rotacion_con_max_bytes_pequeno(self):
        d = self.carpeta("rot")
        info = gen.generate(d, 2000, seed=5, max_bytes=4096)
        self.assertGreater(len(info["files"]), 1)
        self.assertEqual(info["files"], list_log_files(d))
        nombres = [os.path.basename(p) for p in info["files"]]
        esperado = ["events_%03d.log" % i for i in range(1, len(nombres) + 1)]
        self.assertEqual(nombres, esperado)
        reporte, _ = self.calidad(d)
        self.assertEqual(reporte.valid, 2000)
        self.assertEqual(reporte.files, len(nombres))

    # La fraccion de lineas corruptas detectada coincide con la pedida.
    def test_corrupcion_detectada_aproximadamente(self):
        d = self.carpeta("corr")
        info = gen.generate(d, 4000, seed=9, corrupt_rate=0.05)
        reporte, _ = self.calidad(d)
        porcentaje = reporte.corrupt / reporte.lines_read
        self.assertEqual(reporte.corrupt, info["corrupt_lines"])
        self.assertEqual(reporte.valid, 4000)
        self.assertAlmostEqual(porcentaje, 0.05, delta=0.005)

    # Pedir corrupcion no cambia los eventos validos.
    def test_eventos_validos_no_dependen_de_la_corrupcion(self):
        limpia, sucia = self.carpeta("l"), self.carpeta("s")
        gen.generate(limpia, 1500, seed=11, corrupt_rate=0.0)
        gen.generate(sucia, 1500, seed=11, corrupt_rate=0.2)
        _, ev_limpia = self.calidad(limpia)
        _, ev_sucia = self.calidad(sucia)
        self.assertEqual(ev_limpia, ev_sucia)

    # Toda linea corrupta fabricada es rechazada por el lector.
    def test_toda_linea_corrupta_generada_es_rechazada(self):
        rng = random.Random(123)
        tipos = set()
        for _ in range(3000):
            texto = gen.make_corrupt_line(
                rng, "1717000012.412", "S0007", "ENEMY_KILL",
                "type=slime;wave=2")
            self.assertNotIn("\n", texto)
            self.assertIsNone(parse_line(texto + "\n"), repr(texto))
            tipos.add(texto.count("|"))
        self.assertGreater(len(tipos), 3)   # hubo variedad de formas

    # Cada sesion empieza con SESSION_START y termina con SESSION_END; los niveles
    # cuadran con los LEVEL_UP; si murio hay un PLAYER_DEATH justo antes del final; las
    # horas siempre crecen y la duracion coincide con las horas.
    def test_sesiones_coherentes(self):
        d = self.carpeta("coh")
        gen.generate(d, 6000, seed=21)
        _, eventos = self.calidad(d)
        por_sesion = {}
        orden = []
        ultimo_ts = -1.0
        for ev in eventos:
            self.assertGreater(ev["timestamp"], ultimo_ts)   # global creciente
            ultimo_ts = ev["timestamp"]
            sid = ev["session_id"]
            if sid not in por_sesion:
                por_sesion[sid] = []
                orden.append(sid)
            por_sesion[sid].append(ev)
        self.assertEqual(orden, ["S%04d" % i for i in range(1, len(orden) + 1)])
        for sid, evs in por_sesion.items():
            self.assertEqual(evs[0]["event_type"], "SESSION_START")
            self.assertEqual(evs[-1]["event_type"], "SESSION_END")
            self.assertIn(evs[0]["params"]["difficulty"], gen.DIFFICULTIES)
            fin = evs[-1]["params"]
            subidas = sum(1 for e in evs if e["event_type"] == "LEVEL_UP")
            self.assertEqual(fin["level"], 1 + subidas)
            self.assertIn(fin["result"], ("death", "quit"))
            muertes = [e for e in evs if e["event_type"] == "PLAYER_DEATH"]
            if fin["result"] == "death":
                self.assertEqual(len(muertes), 1)
                self.assertIs(evs[-2], muertes[0])
                self.assertIn(muertes[0]["params"]["cause"], gen.ENEMIES)
                self.assertEqual(muertes[0]["params"]["level"], fin["level"])
            else:
                self.assertEqual(muertes, [])
            inicio = evs[0]["timestamp"]
            self.assertAlmostEqual(fin["duration"],
                                   evs[-1]["timestamp"] - inicio, delta=0.06)

    # En hard se recibe mas dano y se saca menos puntaje que en easy.
    def test_hard_mas_dano_y_menos_puntaje_que_easy(self):
        d = self.carpeta("dif")
        gen.generate(d, 40000, seed=2)
        dificultad, puntaje, dano = {}, {}, {}
        for ev in iter_events(d):
            sid, p = ev["session_id"], ev["params"]
            if ev["event_type"] == "SESSION_START":
                dificultad[sid] = p["difficulty"]
            elif ev["event_type"] == "DAMAGE_TAKEN":
                dano[sid] = dano.get(sid, 0) + p["amount"]
            elif ev["event_type"] == "SESSION_END":
                puntaje[sid] = p["score"]

        def media(valores):
            return sum(valores) / len(valores)

        def por_dif(datos, dif, vacio=0):
            return [datos.get(s, vacio) for s in puntaje if dificultad[s] == dif]

        self.assertLess(media(por_dif(puntaje, "hard")),
                        media(por_dif(puntaje, "easy")))
        self.assertGreater(media(por_dif(dano, "hard")),
                           media(por_dif(dano, "easy")))
        # Duracion y puntaje correlacionados: sesiones largas puntuan mas.
        self.assertGreater(max(puntaje.values()), 5 * media(puntaje.values()))

    # Modo '--sessions': cantidad exacta de sesiones.
    def test_modo_sesiones(self):
        d = self.carpeta("ses")
        info = gen.generate(d, seed=2024, n_sessions=40)
        reporte, eventos = self.calidad(d)
        inicios = [e for e in eventos if e["event_type"] == "SESSION_START"]
        self.assertEqual(info["sessions"], 40)
        self.assertEqual(len(inicios), 40)
        self.assertEqual(reporte.valid, info["events"])
        self.assertEqual(reporte.incomplete_sessions, 0)

    # No se pisan bitacoras existentes salvo con overwrite.
    def test_overwrite_y_proteccion(self):
        d = self.carpeta("ow")
        gen.generate(d, 100, seed=1)
        with self.assertRaises(FileExistsError):
            gen.generate(d, 100, seed=1)
        otro = os.path.join(d, "notas.txt")
        with open(otro, "w") as f:
            f.write("no tocar")
        info = gen.generate(d, 50, seed=1, overwrite=True)
        self.assertEqual(info["events"], 50)
        self.assertTrue(os.path.exists(otro))   # solo borra events_NNN.log
        reporte, _ = self.calidad(d)
        self.assertEqual(reporte.valid, 50)

    # Argumentos imposibles dan error claro.
    def test_argumentos_invalidos(self):
        d = self.carpeta("bad")
        with self.assertRaises(ValueError):
            gen.generate(d, 1)
        with self.assertRaises(ValueError):
            gen.generate(d)
        with self.assertRaises(ValueError):
            gen.generate(d, 10, n_sessions=2)
        with self.assertRaises(ValueError):
            gen.generate(d, 10, corrupt_rate=0.9)
        with self.assertRaises(ValueError):
            gen.generate(d, 10, corrupt_rate=-0.1)

    # La interfaz de terminal funciona.
    def test_linea_de_comandos(self):
        d = self.carpeta("cli")
        salida = io.StringIO()
        with contextlib.redirect_stdout(salida):
            codigo = gen.main(["--events", "500", "--out", d, "--seed", "4",
                               "--buffer", "10", "--corrupt-rate", "0.02"])
        self.assertEqual(codigo, 0)
        self.assertIn("Eventos escritos: 500", salida.getvalue())
        with contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(gen.main(["--out", d]), 2)   # sin --events/--sessions


if __name__ == "__main__":
    unittest.main()
