# ======================================================================
# ARCHIVO: telemetry/writer.py - el ESCRITOR de la bitacora
# ======================================================================
# QUE ES: guarda en disco todo lo que ocurre en el juego (una linea por evento).
# FORMATO DE CADA LINEA:  tiempo|id_sesion|tipo_de_evento|clave=valor;clave=valor
#   ejemplo: 1764000000.123|S0001|ENEMY_KILL|type=slime;wave=2
# COSAS IMPORTANTES QUE HACE:
#   - BUFFER: junta varias lineas en memoria y las escribe de golpe (mas rapido).
#   - NUNCA borra: abre siempre en modo 'a' (append = agregar al final).
#   - ROTACION: si el archivo pasa de 512 KB abre otro (events_002.log, ...).
#   - Al cerrar, escribe lo que quede pendiente para no perder datos.
#   - Si el disco falla, el juego no se cae: solo cuenta las lineas perdidas.
# ======================================================================

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
# os: carpetas, tamano de archivos y rutas.
import os
# time: para poner la hora (timestamp) a cada evento.
import time

# Funciones compartidas: escapar texto y nombres de archivo.
from .common import escape, list_log_files, log_filename, log_index

# Valores por defecto: 25 lineas por buffer, 512 KB por archivo.
# EMPTY_VALUE: texto que se escribe si un valor viene vacio (un valor vacio
# haria que la linea se considerara corrupta).
DEFAULT_BUFFER_SIZE = 25
DEFAULT_MAX_BYTES = 512 * 1024
EMPTY_VALUE = "none"   # un valor vacio haria corrupta la linea al leerla


# CLASE TelemetryWriter: el escritor. Recibe la carpeta, el tamano del
# buffer y el tamano maximo de cada archivo.
class TelemetryWriter:
    """Escribe eventos en ``log_dir/events_NNN.log`` con buffer y rotacion.

    Args:
        log_dir: carpeta de las bitacoras (se crea si no existe).
        buffer_size: lineas que se acumulan antes de hacer flush().
        max_bytes: umbral de tamano; al superarlo se abre el siguiente archivo.

    Atributos utiles para pruebas: ``current_path``, ``pending``,
    ``dropped_lines``.
    """

    # Constructor: valida los numeros, prepara las variables internas
    # (buffer vacio, archivo aun no abierto), crea la carpeta si no existe
    # y abre el ultimo archivo de bitacora.
    def __init__(self, log_dir, buffer_size=DEFAULT_BUFFER_SIZE,
                 max_bytes=DEFAULT_MAX_BYTES):
        # Si alguien pasa valores imposibles (menos de 1), avisamos con un error.
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

        # Crea la carpeta de logs si no existe y abre el archivo donde continuar.
        os.makedirs(log_dir, exist_ok=True)
        self._open_latest()

    # ------------------------------------------------------------ API
    @property
    def current_path(self):
        """Ruta del archivo activo."""
        return self._path

    # Propiedad: cuantas lineas estan en memoria esperando ser escritas.
    @property
    def pending(self):
        """Cantidad de lineas en el buffer que aun no estan en disco."""
        return len(self._buffer)

    # REGISTRAR UN EVENTO. Recibe el tipo (ej. ENEMY_KILL), el id de sesion y
    # los datos extra (type=..., wave=...).
    def log(self, event_type, session_id, **params):
        """Registra un evento. Se escribe a disco al llenarse el buffer."""
        # No se puede registrar si el escritor ya se cerro.
        if self._closed:
            raise ValueError("TelemetryWriter ya fue cerrado")
        # ROTACION: se revisa antes de escribir; el archivo que supero el
        # umbral se cierra y la linea nueva va al siguiente archivo.
        if self._size >= self.max_bytes:
            self._rotate()
        # Se arma la linea de texto y se guarda en el buffer, sumando su tamano.
        line = self._build_line(event_type, session_id, params)
        self._buffer.append(line)
        self._size += len(line.encode("utf-8"))
        # Si el buffer se lleno, se escribe todo a disco.
        if len(self._buffer) >= self.buffer_size:
            self.flush()

    # FLUSH: pasa todo lo que hay en el buffer al archivo y lo vacia.
    def flush(self):
        """Escribe el buffer en disco y lo vacia."""
        # Si no hay nada pendiente, no hay nada que hacer.
        if not self._buffer:
            return
        # Escribimos las lineas y forzamos que lleguen al disco.
        try:
            self._file.write("".join(self._buffer))
            self._file.flush()
        # Si el disco falla, no tumbamos el juego: solo contamos las lineas perdidas.
        except OSError:
            # Un fallo de disco no debe tumbar el juego; se cuenta.
            self.dropped_lines += len(self._buffer)
        self._buffer = []

    # CERRAR: escribe lo pendiente y cierra el archivo. Se puede llamar
    # varias veces sin problema.
    def close(self):
        """Vacia el buffer y cierra el archivo. Es idempotente."""
        if self._closed:
            return
        self._closed = True
        try:
            self.flush()
        # 'finally' garantiza que el archivo se cierre incluso si el flush falla.
        finally:
            self._file.close()

    # Estos dos metodos permiten usar el escritor con 'with ... as ...:' y
    # que se cierre solo al terminar el bloque.
    def __enter__(self):
        return self

    # Al salir del bloque 'with' se cierra el escritor.
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

    # Funcion auxiliar que no necesita datos del objeto.
    @staticmethod
    # Convierte un valor a texto escapado; si queda vacio, escribe 'none'.
    def _format_value(value):
        text = "" if value is None else str(value)
        return escape(text) if text.strip() else EMPTY_VALUE

    # ARMA LA LINEA final: 'clave=valor' unidos por ';', y luego
    # timestamp | sesion | tipo | parametros, terminada en salto de linea.
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

    # Abre un archivo en modo 'a' (agregar al final) y calcula su tamano actual.
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
        # Si hacia falta, agregamos el salto de linea faltante.
        if glue:
            self._file.write("\n")
            self._size += 1

    # Funcion auxiliar que no necesita datos del objeto.
    @staticmethod
    # Mira SOLO el ultimo byte del archivo para saber si termina en salto
    # de linea (asi no se carga el archivo entero en memoria).
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

    # ROTAR: escribe lo pendiente, cierra el archivo y abre el siguiente
    # (events_001 -> events_002 -> ...).
    def _rotate(self):
        """Cierra el archivo activo y abre el siguiente (events_N+1.log)."""
        self.flush()
        self._file.close()
        self._index += 1
        self._open(os.path.join(self.log_dir, log_filename(self._index)))
