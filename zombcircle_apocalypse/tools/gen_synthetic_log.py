# ======================================================================
# ARCHIVO: tools/gen_synthetic_log.py - generador de bitacoras FALSAS (sinteticas)
# ======================================================================
# QUE ES: fabrica bitacoras con partidas inventadas pero realistas. Sirve para:
#   - Los experimentos A, B y C (necesitan 5 000, 50 000 y 100 000 eventos).
#   - La version web (pygbag), que arranca con una bitacora ya creada.
#   - Probar el programa con datos corruptos a proposito (--corrupt-rate).
# Con la misma 'semilla' (--seed) siempre genera exactamente los mismos datos.
# COMO SE USA:  python tools/gen_synthetic_log.py --events 100000 --out carpeta --seed 42
# ======================================================================

"""Generador de bitacoras sinteticas para experimentos y demostracion web.

Uso por linea de comandos (desde la raiz del repo):

    python tools/gen_synthetic_log.py --events 100000 --out carpeta --seed 42
    python tools/gen_synthetic_log.py --sessions 40 --out logs --seed 2024 --overwrite

Opciones: --events N | --sessions N (una de las dos), --out CARPETA,
--seed 42, --max-bytes 524288, --buffer 100, --corrupt-rate 0.0, --overwrite.

Uso como modulo (lo usan los experimentos A, B y C):

    from tools.gen_synthetic_log import generate
    info = generate("tmp_logs", 100000, seed=42, buffer_size=100)
    info["events"], info["sessions"], info["files"], info["bytes"]

DECISIONES DE DISENO (para el informe)
--------------------------------------
- Escribe con TelemetryWriter (subclase minima), asi se prueba tambien la
  rotacion, el buffer y el escape del formato real.
- NUMERO EXACTO DE EVENTOS: ``generate(n_events=N)`` escribe exactamente N
  eventos validos y TODAS las sesiones quedan completas. Cada sesion tiene
  un tamano natural; cuando quedan pocos eventos, la ULTIMA sesion se
  recorta (o se alarga 1 evento) para cerrar justo en N. Se eligio exacto y
  no "el mas cercano" porque los experimentos piden tamanos de 5 000, 50 000
  y 100 000 y las tablas deben decir lo mismo que el archivo. Minimo N = 2
  (SESSION_START + SESSION_END con result=quit).
- Reproducible: random.Random(seed) propio (nunca el estado global) y
  timestamps SINTETICOS (milisegundos enteros desde una epoca fija), por lo
  que el mismo seed produce los mismos bytes sin depender del reloj.
- Los eventos validos NO dependen de --corrupt-rate: la corrupcion usa un
  generador aparte (derivado del seed) e INSERTA lineas corruptas entre los
  eventos. Con o sin corrupcion el lector entrega los mismos eventos validos.
  La fraccion de lineas corruptas sobre el total de lineas es ~corrupt_rate.
"""
# Librerias: opciones de terminal, rutas, numeros al azar y sys.
import argparse
import os
import random
import sys

# Raiz del proyecto en la ruta de Python para poder importar 'telemetry'.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Usamos el escritor REAL del juego (asi tambien se prueba).
from telemetry import TelemetryWriter
from telemetry.common import list_log_files

EPOCH_MS = 1717000000000        # 2024-05-29, el ejemplo del enunciado
# Nombres de jugadores, tipos de enemigo, dificultades y puntos por matar a cada uno.
PLAYERS = ("ana", "luis", "marta", "pedro", "sofia", "juan", "camila", "diego")
ENEMIES = ("slime", "bat", "brute", "boss")
DIFFICULTIES = ("easy", "normal", "hard")
KILL_POINTS = {"slime": 10, "bat": 25, "brute": 60, "boss": 300}
MAX_BODY = 300                  # tope de eventos intermedios por sesion
MAX_CORRUPT_RATE = 0.5

# Perfil por dificultad: hard = mas dano y menos puntaje que easy.
PROFILES = {
    "easy":   {"weight": 0.35, "p_death": 0.60, "dmg": (4, 12),
               "dmg_frac": 0.18, "lvl_rate": 1.25, "score_mult": 1.15},
    "normal": {"weight": 0.40, "p_death": 0.72, "dmg": (7, 18),
               "dmg_frac": 0.28, "lvl_rate": 1.00, "score_mult": 1.00},
    "hard":   {"weight": 0.25, "p_death": 0.85, "dmg": (12, 30),
               "dmg_frac": 0.40, "lvl_rate": 0.80, "score_mult": 0.82},
}

# Maneras de danar una linea a proposito.
CORRUPT_KINDS = ("vacia", "espacios", "truncada", "sin_igual", "score_abc",
                 "tres_campos", "cinco_campos")


# ESCRITOR SINTETICO: igual al real pero con reloj falso (para que los datos
# sean repetibles) y con capacidad de escribir lineas crudas (corruptas).
class _SyntheticWriter(TelemetryWriter):
    """TelemetryWriter con reloj sintetico y escritura de lineas crudas."""

    # Arranca el reloj falso y llama al constructor del escritor real.
    def __init__(self, log_dir, buffer_size, max_bytes):
        self._clock_ms = EPOCH_MS
        self._raw = None
        super().__init__(log_dir, buffer_size, max_bytes)

    # Fija la hora del siguiente evento.
    def set_clock(self, ms):
        """Fija el instante (ms enteros) del siguiente evento."""
        self._clock_ms = ms

    # Usa el reloj falso en vez del reloj real, siempre creciendo.
    def _next_timestamp(self):
        ts = round(self._clock_ms / 1000.0, 3)
        if ts <= self._last_ts:                 # estrictamente creciente
            ts = round(self._last_ts + 0.001, 3)
        self._last_ts = ts
        return ts

    # Escribe una linea tal cual (se usa para meter lineas corruptas).
    def write_raw(self, text):
        """Escribe ``text`` + salto de linea por el mismo camino de log()."""
        self._raw = text
        try:
            self.log("RAW", "RAW")
        finally:
            self._raw = None

    # Si hay una linea cruda pendiente, la devuelve; si no, arma la normal.
    def _build_line(self, event_type, session_id, params):
        if self._raw is not None:
            return self._raw + "\n"
        return super()._build_line(event_type, session_id, params)


# ---------------------------------------------------------------- sesiones
def _enemy_weights(level, damage):
    """Pesos (slime, bat, brute, boss); el jefe aparece en niveles altos."""
    if damage:
        boss = 0.0 if level < 2 else min(0.06 + 0.03 * level, 0.25)
    else:
        boss = 0.0 if level < 3 else 0.03
    rest = 1.0 - boss
    return (rest * 0.52, rest * 0.28, rest * 0.20, boss)


# 'Sortea' el plan de una partida: dificultad, jugador, cuantos eventos
# intermedios tendra (con distribucion de cola larga) y si termina en muerte.
def _draw_plan(rng):
    """Dificultad, jugador, eventos intermedios y si la sesion termina en muerte."""
    difficulty = rng.choices(DIFFICULTIES,
                             [PROFILES[d]["weight"] for d in DIFFICULTIES])[0]
    player = rng.choice(PLAYERS)
    effort = rng.lognormvariate(0.0, 0.65)        # cola larga
    body = int(round(16 * effort * rng.uniform(0.85, 1.15)))
    body = min(MAX_BODY, max(1, body))
    death = rng.random() < PROFILES[difficulty]["p_death"]
    return difficulty, player, body, death


# Construye TODOS los eventos de UNA partida: empieza con SESSION_START,
# reparte subidas de nivel, danos y muertes de enemigos en el tiempo, agrega
# PLAYER_DEATH si murio y cierra con SESSION_END (con puntaje calculado).
def _session_events(rng, session_id, t0, difficulty, player, body_len, death):
    """Lista de (t_ms, tipo, sesion, params) de UNA sesion completa.

    Total de eventos = 2 + (1 si death) + body_len.
    """
    # Perfil de la dificultad y evento inicial.
    prof = PROFILES[difficulty]
    events = [(t0, "SESSION_START", session_id,
               {"player": player, "difficulty": difficulty})]

    # Cuantos eventos de nivel, dano y muertes de enemigos habra, mezclados al azar.
    n_lvl = min(body_len, int(round(body_len * rng.uniform(0.04, 0.12)
                                    * prof["lvl_rate"])))
    frac = min(0.7, max(0.05, rng.gauss(prof["dmg_frac"], 0.05)))
    n_dmg = int(round((body_len - n_lvl) * frac))
    n_kill = body_len - n_lvl - n_dmg
    kinds = ["L"] * n_lvl + ["D"] * n_dmg + ["K"] * n_kill
    rng.shuffle(kinds)

    # Duracion objetivo ~ proporcional a los eventos (correlacion con ruido).
    duration_ms = int((15 + body_len * rng.uniform(2.0, 4.0)) * 1000)
    offsets = sorted(rng.randrange(500, duration_ms) for _ in kinds)

    level = 1
    points = 0
    last_source = None
    last_t = t0
    # Para cada evento intermedio se crea el tipo que toca (LEVEL_UP, DAMAGE_TAKEN
    # o ENEMY_KILL) con sus datos.
    for kind, off in zip(kinds, offsets):
        t = max(t0 + off, last_t + 1)             # estrictamente creciente
        last_t = t
        if kind == "L":
            level += 1
            events.append((t, "LEVEL_UP", session_id,
                           {"level": level,
                            "time": round((t - t0) / 1000.0, 1)}))
        elif kind == "D":
            source = rng.choices(ENEMIES, _enemy_weights(level, True))[0]
            amount = rng.randint(*prof["dmg"]) + (level - 1)
            last_source = source
            events.append((t, "DAMAGE_TAKEN", session_id,
                           {"amount": amount, "source": source}))
        else:
            enemy = rng.choices(ENEMIES, _enemy_weights(level, False))[0]
            points += KILL_POINTS[enemy]
            events.append((t, "ENEMY_KILL", session_id,
                           {"type": enemy, "wave": level}))

    # Cierre de la partida: muerte (si aplica) y duracion.
    end_t = max(last_t + 1, t0 + duration_ms)
    if death:
        # Causa = tipo de enemigo que hizo el ultimo dano (coherencia).
        cause = last_source or rng.choices(ENEMIES,
                                           _enemy_weights(level, True))[0]
        events.append((end_t, "PLAYER_DEATH", session_id,
                       {"cause": cause, "level": level}))
        end_t += rng.randint(5, 40)
    duration = round((end_t - t0) / 1000.0, 1)

    # Puntaje final = puntos + tiempo, ajustado por dificultad y algo de azar;
    # de vez en cuando sale un puntaje atipico a proposito.
    raw = points + 3.0 * duration
    score = raw * prof["score_mult"] * rng.lognormvariate(0.0, 0.25)
    if rng.random() < 0.015:                      # atipico ocasional
        score *= rng.uniform(3.0, 6.0)
    score = int(round(score / 10.0)) * 10
    events.append((end_t, "SESSION_END", session_id,
                   {"score": score, "level": level, "duration": duration,
                    "result": "death" if death else "quit"}))
    return events, end_t


# Genera partidas una tras otra hasta completar N eventos (exactos) o N partidas.
# La ultima partida se ajusta para que el total sea justo N.
def _iter_sessions(rng, n_events=None, n_sessions=None, start_ms=EPOCH_MS):
    """Genera sesiones (listas de eventos) hasta N eventos o N sesiones."""
    t0 = start_ms + rng.randint(0, 5000)
    written = 0
    k = 0
    while True:
        if n_sessions is not None and k >= n_sessions:
            return
        if n_events is not None and written >= n_events:
            return
        k += 1
        difficulty, player, body, death = _draw_plan(rng)
        if n_events is not None:
            length = 2 + int(death) + body
            rem = n_events - written
            # Que no sobre un solo evento (una sesion minima mide 2).
            if rem - length < 2 and rem != length:
                length = rem
            if length < 3:
                death = False
            body = length - 2 - int(death)
        events, end_t = _session_events(rng, "S%04d" % k, t0, difficulty,
                                        player, body, death)
        written += len(events)
        yield events
        t0 = end_t + rng.randint(2000, 600000)


# --------------------------------------------------------------- corrupcion
def make_corrupt_line(rng, ts, session_id, event_type, params_text):
    """Linea corrupta (SIN salto final) que parse_line SIEMPRE rechaza."""
    kind = rng.choice(CORRUPT_KINDS)
    head = "%s|%s|%s" % (ts, session_id, event_type)
    base = "%s|%s" % (head, params_text)
    if kind == "vacia":
        return ""
    if kind == "espacios":
        return " " * rng.randint(1, 6)
    if kind == "truncada":
        # Corte antes del 3er "|": maximo 3 campos, nunca puede ser valida.
        bars = [i for i, c in enumerate(base) if c == "|"]
        return base[:rng.randint(1, bars[2])]
    if kind == "sin_igual":
        return head + "|scoreabc"
    if kind == "score_abc":
        return head + "|score=abc"
    if kind == "tres_campos":
        return head
    return base + "|extra"                        # cinco campos


# Convierte los parametros a texto 'clave=valor;clave=valor'.
def _params_text(params):
    return ";".join("%s=%s" % (k, v) for k, v in params.items())


# ------------------------------------------------------------------ generate
def generate(out_dir, n_events=None, seed=42, max_bytes=512 * 1024,
             buffer_size=100, corrupt_rate=0.0, overwrite=False,
             n_sessions=None):
    """Escribe una bitacora sintetica en ``out_dir`` y resume lo escrito.

    Pasar exactamente UNO de ``n_events`` (cuenta exacta de eventos validos,
    sesiones completas) o ``n_sessions`` (cantidad exacta de sesiones).

    Si ``out_dir`` ya tiene events_NNN.log: FileExistsError, salvo
    ``overwrite=True``, que borra SOLO esos archivos (nada mas).

    Devuelve dict: events, sessions, files (rutas en orden), bytes (suma de
    tamanos), corrupt_lines, lines (eventos + corruptas), seed, out_dir.
    """
    # Validaciones de los argumentos.
    if (n_events is None) == (n_sessions is None):
        raise ValueError("indica exactamente uno: n_events o n_sessions")
    if n_events is not None and n_events < 2:
        raise ValueError("n_events debe ser >= 2")
    if n_sessions is not None and n_sessions < 1:
        raise ValueError("n_sessions debe ser >= 1")
    if not 0.0 <= corrupt_rate <= MAX_CORRUPT_RATE:
        raise ValueError("corrupt_rate debe estar entre 0 y %s" % MAX_CORRUPT_RATE)

    # Si la carpeta ya tiene bitacoras: error, salvo que se pida 'overwrite'
    # (entonces solo se borran esos archivos).
    existing = list_log_files(out_dir)
    if existing:
        if not overwrite:
            raise FileExistsError("%s ya tiene bitacoras (usa overwrite)" % out_dir)
        for path in existing:
            os.remove(path)

    # Dos generadores de azar separados: uno para eventos, otro para corrupcion
    # (asi la corrupcion nunca cambia los eventos validos).
    rng = random.Random(seed)
    crng = random.Random("corrupt:%s" % seed)     # aparte: no altera los eventos

    # Preparamos las partidas y el total de eventos.
    sessions = _iter_sessions(rng, n_events, n_sessions)
    if n_sessions is not None:
        sessions = list(sessions)                 # pocas: se necesita el total
        total = sum(len(s) for s in sessions)
    else:
        total = n_events

    # Calculamos cuantas lineas corruptas insertar y en que posiciones.
    n_corrupt = int(round(total * corrupt_rate / (1.0 - corrupt_rate)))
    slots = {}
    for _ in range(n_corrupt):
        slot = crng.randrange(total + 1)
        slots[slot] = slots.get(slot, 0) + 1

    written = 0
    n_sess = 0
    last = ("%.3f" % (EPOCH_MS / 1000.0), "S0001", "SESSION_START",
            "player=ana;difficulty=easy")

    # Ayudante: inserta las lineas corruptas que correspondan en esa posicion.
    def put_corrupt(writer, slot):
        for _ in range(slots.pop(slot, 0)):
            writer.write_raw(make_corrupt_line(crng, *last))

    # Escribimos todos los eventos (con las lineas corruptas intercaladas).
    with _SyntheticWriter(out_dir, buffer_size, max_bytes) as writer:
        for session in sessions:
            n_sess += 1
            for t_ms, event_type, sid, params in session:
                put_corrupt(writer, written)
                writer.set_clock(t_ms)
                writer.log(event_type, sid, **params)
                written += 1
                last = ("%.3f" % (t_ms / 1000.0), sid, event_type,
                        _params_text(params))
        put_corrupt(writer, written)

    # Resumen final de lo escrito.
    files = list_log_files(out_dir)
    return {"events": written, "sessions": n_sess, "files": files,
            "bytes": sum(os.path.getsize(p) for p in files),
            "corrupt_lines": n_corrupt, "lines": written + n_corrupt,
            "seed": seed, "out_dir": out_dir}


# Devuelve los eventos en una lista en memoria SIN escribirlos a disco
# (para medir el escritor sin medir tambien la generacion).
def build_events(n_events, seed=42):
    """Lista de exactamente ``n_events`` eventos en memoria (sin escribir).

    Cada elemento es (t_ms, tipo, session_id, params). Son los MISMOS eventos
    que escribiria ``generate`` con ese seed; los experimentos los usan para
    medir solo el costo del escritor, sin el costo de generarlos.
    """
    if n_events < 2:
        raise ValueError("n_events debe ser >= 2")
    rng = random.Random(seed)
    eventos = []
    for sesion in _iter_sessions(rng, n_events=n_events):
        eventos.extend(sesion)
    return eventos


# ----------------------------------------------------------------------- CLI
def main(argv=None):
    # Definicion de las opciones (--events, --sessions, --out, --seed...).
    parser = argparse.ArgumentParser(
        description="Genera una bitacora sintetica de Zombcircle Apocalypse.")
    parser.add_argument("--events", type=int, help="eventos validos exactos")
    parser.add_argument("--sessions", type=int, help="sesiones exactas")
    parser.add_argument("--out", required=True, help="carpeta de salida")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--max-bytes", type=int, default=512 * 1024)
    parser.add_argument("--buffer", type=int, default=100)
    parser.add_argument("--corrupt-rate", type=float, default=0.0)
    parser.add_argument("--overwrite", action="store_true",
                        help="borra los events_NNN.log existentes en --out")
    args = parser.parse_args(argv)
    # Si algo esta mal, se muestra el error y se devuelve el codigo 2.
    try:
        info = generate(args.out, args.events, args.seed, args.max_bytes,
                        args.buffer, args.corrupt_rate, args.overwrite,
                        args.sessions)
    except (ValueError, FileExistsError) as exc:
        print("Error: %s" % exc, file=sys.stderr)
        return 2
    # Resumen en pantalla.
    print("Eventos escritos: %s" % format(info["events"], ","))
    print("Sesiones: %s" % format(info["sessions"], ","))
    print("Lineas corruptas insertadas: %s" % format(info["corrupt_lines"], ","))
    print("Archivos: %d" % len(info["files"]))
    print("Bytes totales: %s" % format(info["bytes"], ","))
    print("Carpeta: %s" % info["out_dir"])
    return 0


# Solo se ejecuta al abrir el archivo directamente.
if __name__ == "__main__":
    sys.exit(main())
