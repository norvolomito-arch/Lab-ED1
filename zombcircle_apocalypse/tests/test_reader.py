# ======================================================================
# ARCHIVO: tests/test_reader.py - pruebas del lector de bitacora
# ======================================================================
# QUE PRUEBA: telemetry/reader.py: que las lineas corruptas se rechacen, que el
# orden de archivos sea numerico, que las carpetas vacias o inexistentes no den
# error y que los numeros se conviertan al tipo correcto.
# QUE SON LOS TESTS: son programitas que prueban que el codigo funciona.
# Cada funcion 'test_...' hace una comprobacion y, si el resultado no es el
# esperado, falla y avisa. Sirven para detectar errores antes de entregar.
# COMO CORRERLOS (desde la carpeta del proyecto):  python -m unittest discover -s tests
# PALABRAS: 'assertEqual(a, b)' = comprueba que a y b sean iguales;
# 'setUp' = preparacion antes de cada prueba; 'tearDown' = limpieza despues.
# ======================================================================

"""Tests for robust streaming event log parsing."""

# Librerias para rutas, carpetas temporales y pruebas.
import os
import tempfile
import unittest

# Lo que vamos a probar.
from telemetry import iter_events, parse_line


# PRUEBAS DEL LECTOR.
class TelemetryReaderTests(unittest.TestCase):
    # Antes de cada prueba se crea una carpeta temporal para las bitacoras.
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.log_dir = os.path.join(self.temp_dir.name, "logs")
        os.makedirs(self.log_dir)

    # Despues de cada prueba, la carpeta temporal se borra.
    def tearDown(self):
        self.temp_dir.cleanup()

    # Ayudante: crea un archivo de bitacora con las lineas dadas.
    def write_log(self, filename, contents):
        path = os.path.join(self.log_dir, filename)
        with open(path, "w", encoding="utf-8") as log_file:
            for line in contents:
                log_file.write(line)
        return path

    # Cada tipo de linea mala (vacia, pocos campos, campos de mas, sin '=',
    # valor vacio, numero invalido, tiempo invalido) debe ser rechazada.
    def test_parse_line_rejects_each_required_corrupt_case(self):
        corrupt_lines = (
            "",
            "   \t",
            "1.0|S0001|CUSTOM",
            "1.0|S0001|CUSTOM|value=1|extra",
            "1.0|S0001|CUSTOM|missing_equals",
            "1.0|S0001|CUSTOM|player=",
            "1.0|S0001|SESSION_END|score=abc",
            "not-a-timestamp|S0001|CUSTOM|",
        )
        for line in corrupt_lines:
            with self.subTest(line=line):
                self.assertIsNone(parse_line(line))

    # Una ultima linea sin salto final (truncada) se descarta.
    def test_iter_events_discards_an_unterminated_last_line(self):
        complete = "1.0|S0001|SESSION_START|player=ana\n"
        truncated = "2.0|S0001|SESSION_END|score=10"
        self.write_log("events_001.log", (complete, truncated))

        events = list(iter_events(self.log_dir))

        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["event_type"], "SESSION_START")

    # Carpeta inexistente: cero eventos y sin error.
    def test_missing_directory_returns_no_events(self):
        missing_dir = os.path.join(self.temp_dir.name, "missing")
        self.assertEqual(list(iter_events(missing_dir)), [])

    # Carpeta vacia: cero eventos.
    def test_empty_directory_returns_no_events(self):
        self.assertEqual(list(iter_events(self.log_dir)), [])

    # events_999 se lee antes que events_1000 (orden numerico).
    def test_log_files_are_ordered_numerically(self):
        self.write_log("events_1000.log", ("2.0|S1000|CUSTOM|value=1000\n",))
        self.write_log("events_999.log", ("1.0|S0999|CUSTOM|value=999\n",))

        events = list(iter_events(self.log_dir))

        self.assertEqual([event["session_id"] for event in events],
                         ["S0999", "S1000"])

    # score, level, amount y wave salen enteros; duration y time, decimales.
    def test_numeric_values_are_converted_to_int_or_float(self):
        line = (
            "1.5|S0001|SESSION_END|score=3200;level=4;duration=77.6;"
            "amount=12;wave=2;time=1.25\n"
        )
        self.write_log("events_001.log", (line,))

        event = next(iter_events(self.log_dir))
        params = event["params"]

        self.assertIs(type(params["score"]), int)
        self.assertIs(type(params["level"]), int)
        self.assertIs(type(params["amount"]), int)
        self.assertIs(type(params["wave"]), int)
        self.assertIs(type(params["duration"]), float)
        self.assertIs(type(params["time"]), float)
        self.assertIs(type(event["timestamp"]), float)
        self.assertEqual(params["score"], 3200)
        self.assertEqual(params["duration"], 77.6)


# Permite correr solo este archivo.
if __name__ == "__main__":
    unittest.main()