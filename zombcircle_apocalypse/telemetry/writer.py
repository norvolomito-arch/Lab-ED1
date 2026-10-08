"""Escritura de la bitacora de eventos (Persona 1).

Formato de cada linea (exactamente 4 campos separados por "|"):

    timestamp|session_id|event_type|clave=valor;clave=valor

Garantias del escritor:
- Siempre abre en modo "a": nunca sobrescribe una bitacora existente.
- Escribe durante la partida (buffer de N lineas), no al final.
- close() vacia el buffer pendiente (usar try/finally o ``with``).
- Rotacion por tamano: events_001.log -> events_002.log -> ...
- Al iniciar continua desde el ultimo archivo existente de ``log_dir``.
- Los valores se escapan con ``common.escape`` (ver ese modulo): un valor
  con "|", ";" o "=" no puede cambiar el significado de la linea.
"""
import os
import time

from .common import escape, list_log_files, log_filename, log_index

DEFAULT_BUFFER_SIZE = 25
DEFAULT_MAX_BYTES = 512 * 1024
EMPTY_VALUE = "none"   # un valor vacio haria corrupta la linea al leerla


class TelemetryWriter:
    """Escribe eventos en ``log_dir/events_NNN.log`` con buffer y rotacion.

    Args:
        log_dir: carpeta de las bitacoras (se crea si no existe).
        buffer_size: lineas que se acumulan antes de hacer flush().
        max_bytes: umbral de tamano; al superarlo se abre el siguiente archivo.

    Atributos utiles para pruebas: ``current_path``, ``pending``,
    ``dropped_lines``.
    """

    def __init__(self, log_dir, buffer_size=DEFAULT_BUFFER_SIZE,
                 max_bytes=DEFAULT_MAX_BYTES):
        if buffer_size < 1:
            raise ValueError("buffer_size debe ser >= 1")
        if max_bytes < 1:
            raise ValueError("max_bytes debe ser >= 1")
        self.log_dir = log_dir
        self.buffer_size = buffer_size
        self.max_bytes = max_bytes
        self.dropped_lines = 0     # lineas perdidas por errores de disco

        self._buffer = []          # lineas pendientes (maximo buffer_size)
        self._file = None
        self._path = None
        self._index = 1
        self._size = 0             # bytes en disco + bytes en el buffer
        self._last_ts = 0.0
        self._closed = False

        os.makedirs(log_dir, exist_ok=True)
        self._open_latest()

    # ------------------------------------------------------------ API
    @property
    def current_path(self):
        """Ruta del archivo activo."""
        return self._path

    @property
    def pending(self):
        """Cantidad de lineas en el buffer que aun no estan en disco."""
        return len(self._buffer)

    def log(self, event_type, session_id, **params):
        """Registra un evento. Se escribe a disco al llenarse el buffer."""
        if self._closed:
            raise ValueError("TelemetryWriter ya fue cerrado")
        # ROTACION: se revisa antes de escribir; el archivo que supero el
        # umbral se cierra y la linea nueva va al siguiente archivo.
        if self._size >= self.max_bytes:
            self._rotate()
        line = self._build_line(event_type, session_id, params)
        self._buffer.append(line)
        self._size += len(line.encode("utf-8"))
        if len(self._buffer) >= self.buffer_size:
            self.flush()

    def flush(self):
        """Escribe el buffer en disco y lo vacia."""
        if not self._buffer:
            return
        try:
            self._file.write("".join(self._buffer))
            self._file.flush()
        except OSError:
            # Un fallo de disco no debe tumbar el juego; se cuenta.
            self.dropped_lines += len(self._buffer)
        self._buffer = []

    def close(self):
        """Vacia el buffer y cierra el archivo. Es idempotente."""
        if self._closed:
            return
        self._closed = True
        try:
            self.flush()
        finally:
            self._file.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()
        return False

    # -------------------------------------------------------- formato
    def _next_timestamp(self):
        """Timestamp con 3 decimales, estrictamente creciente."""
        ts = round(time.time(), 3)
        if ts <= self._last_ts:
            ts = round(self._last_ts + 0.001, 3)
        self._last_ts = ts
        return ts

    @staticmethod
    def _format_value(value):
        text = "" if value is None else str(value)
        return escape(text) if text.strip() else EMPTY_VALUE

    def _build_line(self, event_type, session_id, params):
        pairs = ";".join("%s=%s" % (escape(key), self._format_value(value))
                         for key, value in params.items())
        return "%.3f|%s|%s|%s\n" % (self._next_timestamp(),
                                    escape(session_id),
                                    escape(event_type), pairs)

    # ------------------------------------------------------- ROTACION
    def _open_latest(self):
        """Continua en el ultimo archivo de log_dir (o crea events_001)."""
        files = list_log_files(self.log_dir)
        if files:
            self._index = log_index(files[-1])
            self._open(files[-1])
        else:
            self._index = 1
            self._open(os.path.join(self.log_dir, log_filename(1)))

    def _open(self, path):
        """Abre ``path`` en modo "a" y calcula su tamano actual."""
        try:
            size = os.path.getsize(path)
        except OSError:
            size = 0
        # Si el programa anterior se cerro de golpe, la ultima linea pudo
        # quedar sin "\n". Sin este salto, la primera linea nueva se pegaria
        # a la truncada y se perderian dos eventos en vez de uno.
        glue = size > 0 and self._ends_without_newline(path, size)
        # newline="\n": en Windows no se traduce a "\r\n", asi el conteo de
        # bytes coincide con el tamano real del archivo.
        self._file = open(path, "a", encoding="utf-8", newline="\n")
        self._path = path
        self._size = size
        if glue:
            self._file.write("\n")
            self._size += 1

    @staticmethod
    def _ends_without_newline(path, size):
        """True si el ultimo byte del archivo no es "\n".

        Se lee solo el ULTIMO byte con seek + readline (no read()), asi la
        memoria no depende del tamano de la bitacora.
        """
        try:
            with open(path, "rb") as f:
                f.seek(size - 1)
                return f.readline() != b"\n"
        except OSError:
            return False

    def _rotate(self):
        """Cierra el archivo activo y abre el siguiente (events_N+1.log)."""
        self.flush()
        self._file.close()
        self._index += 1
        self._open(os.path.join(self.log_dir, log_filename(self._index)))
