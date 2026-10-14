# ======================================================================
# ARCHIVO: game/statistics_engine.py - el ANALISIS de los datos (Persona 3)
# ======================================================================
# QUE ES: lee la bitacora y la convierte en tablas y numeros listos para mostrar.
# PASOS: (1) recorre los eventos y arma un resumen por partida (puntaje,
# duracion, dano recibido, nivel, causa de muerte); (2) calcula estadisticas de
# esos resumenes; (3) arma tablas de frecuencia, histograma, progresion por
# nivel, comparacion por dificultad y correlaciones.
# Las formulas basicas (media, mediana, etc.) las trae descriptive_stats.py.
# Este archivo NO dibuja nada: solo calcula. Dibuja statistics_screen.py.
# ======================================================================

"""
Motor de analisis de Persona 3.

"""
# math: para raices cuadradas.
import math

# Lector de la bitacora: entrega los eventos uno por uno.
from telemetry import iter_events

# Formulas estadisticas hechas a mano (archivo de Persona 2).
from game.descriptive_stats import (
    RunningStats, atipicos_z, cuartiles, mediana, percentil_rango_mas_cercano,
)


# Crea el 'resumen vacio' de una partida: puntaje 0, duracion 0,
# dano 0, nivel 1, dificultad desconocida, causa desconocida, sin terminar.
def _new_session():
    return {
        "score": 0.0,
        "duration": 0.0,
        "damage": 0.0,
        "level": 1,
        "difficulty": None,
        "cause": "unknown",
        "max_level": 1,
        "finished": False,
    }


# Guarda una copia del resumen de la partida ya terminada.
def _finish_session(sessions, sid, current):
    if not current:
        return
    sessions[sid] = dict(current)


# Recorre TODOS los eventos y arma un diccionario {id_sesion: resumen}.
# Solo se guardan las partidas que terminaron (tienen SESSION_END).
def collect_sessions(log_dir):

    # 'sessions' = partidas terminadas; 'active' = partidas en curso.
    sessions = {}
    active = {}

    # Leemos evento por evento (sin cargar toda la bitacora).
    for event in iter_events(log_dir):
        sid = event["session_id"]
        etype = event["event_type"]
        params = event["params"]

        # Empieza una partida: creamos su resumen con la dificultad elegida.
        if etype == "SESSION_START":
            state = _new_session()
            state["difficulty"] = params.get("difficulty", "unknown")
            active[sid] = state

        # Si el evento pertenece a una partida abierta, segun su tipo:
        elif sid in active:
            state = active[sid]

            # DAMAGE_TAKEN: sumamos el dano recibido.
            if etype == "DAMAGE_TAKEN":
                state["damage"] += float(params.get("amount", 0))

            # PLAYER_DEATH: guardamos la causa de muerte y el nivel.
            elif etype == "PLAYER_DEATH":
                state["cause"] = str(params.get("cause", "unknown"))
                state["level"] = int(params.get("level", state["level"]))
                state["max_level"] = max(state["max_level"], state["level"])

            # LEVEL_UP: actualizamos el nivel y el nivel maximo alcanzado.
            elif etype == "LEVEL_UP":
                level = int(params.get("level", state["level"]))
                state["level"] = level
                state["max_level"] = max(state["max_level"], level)

            # SESSION_END: guardamos puntaje, duracion y nivel finales; si no hubo
            # muerte (el jugador abandono) la causa es el 'result'. Luego pasamos
            # la partida a la lista de terminadas.
            elif etype == "SESSION_END":
                state["score"] = float(params.get("score", 0))
                state["duration"] = float(params.get("duration", 0))
                state["level"] = int(params.get("level", state["level"]))
                state["max_level"] = max(state["max_level"], state["level"])
                state["finished"] = True
                if state["cause"] == "unknown":      # abandono con ESC: sin PLAYER_DEATH
                    state["cause"] = str(params.get("result", "unknown"))
                _finish_session(sessions, sid, state)
                del active[sid]

    # Devolvemos las partidas terminadas.
    return sessions


# Separa tres listas de numeros (puntaje, duracion, dano) de todas las partidas.
def _numeric_values(sessions):
    return {
        "score": [s["score"] for s in sessions.values()],
        "duration": [s["duration"] for s in sessions.values()],
        "damage": [s["damage"] for s in sessions.values()],
    }


# Calcula TODAS las estadisticas de una lista de numeros:
# media, varianza, desviacion, CV, min, max, rango (una pasada) y
# mediana, cuartiles, P90, IQR, limites y atipicos (necesitan ordenar).
def basic_distribution(values):
    """Resumen de una variable numerica (usa descriptive_stats, Persona 2).

    - Medidas de UNA pasada (n, suma, min, max, rango, media, varianza,
      desviacion, CV): RunningStats las acumula sin guardar los datos.
    - Medidas de ORDEN (mediana, cuartiles, P90, atipicos): usan la lista
      ordenada, por eso necesitan memoria proporcional a n.
    """
    # Alimentamos la 'libretita' RunningStats numero por numero.
    stats = RunningStats()
    for v in values:
        stats.add(float(v))

    # Si no hay datos, devolvemos todo en cero para no fallar.
    if stats.n == 0:
        return {
            "n": 0, "sum": 0.0, "mean": 0.0, "variance": 0.0, "std": 0.0,
            "cv": 0.0, "min": 0.0, "max": 0.0, "range": 0.0,
            "median": 0.0, "q1": 0.0, "q3": 0.0, "p90": 0.0,
            "iqr": 0.0, "lower": 0.0, "upper": 0.0,
            "outliers": [], "z_outliers": [],
        }

    # Ordenamos los datos (necesario para mediana y cuartiles).
    data = sorted(float(v) for v in values)
    if stats.n == 1:
        q1 = q3 = data[0]
    else:
        q1, q3 = cuartiles(data)
    # IQR y limites de la regla de Tukey para detectar atipicos.
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr

    # Devolvemos todos los resultados juntos en un diccionario.
    return {
        "n": stats.n,
        "sum": stats.total,
        "mean": stats.media,
        "variance": stats.varianza_muestral or 0.0,
        "std": stats.desviacion or 0.0,
        "cv": stats.cv_porcentaje or 0.0,
        "min": stats.minimum,
        "max": stats.maximum,
        "range": stats.rango,
        "median": mediana(data),
        "q1": q1,
        "q3": q3,
        "p90": percentil_rango_mas_cercano(data, 90),
        "iqr": iqr,
        "lower": lower,
        "upper": upper,
        "outliers": [x for x in data if x < lower or x > upper],
        "z_outliers": atipicos_z(data, 3.0),
    }


# TABLA DE FRECUENCIAS de una columna (ej. causa de muerte): cuenta cuantas
# veces sale cada valor, sin usar Counter. Devuelve frecuencia, proporcion
# y proporcion acumulada, de mayor a menor.
def frequency_table(sessions, field):
    # Contamos manualmente cada valor con un diccionario.
    counts = {}
    for session in sessions.values():
        value = str(session.get(field, "unknown"))
        counts[value] = counts.get(value, 0) + 1

    # Ordenamos de mas frecuente a menos y calculamos relativa y acumulada.
    total = sum(counts.values())
    rows = []
    cumulative = 0
    for value, count in sorted(counts.items(), key=lambda item: (-item[1], item[0])):
        cumulative += count
        rows.append({
            "value": value,
            "frequency": count,
            "relative": count / total if total else 0.0,
            "cumulative": cumulative / total if total else 0.0,
        })

    return rows


# MODA: el valor mas frecuente (el primero de la tabla ordenada).
def mode_from_frequency(rows):
    return rows[0]["value"] if rows else "N/A"


# HISTOGRAMA: reparte los datos en k intervalos del mismo ancho y cuenta
# cuantos caen en cada uno.
def histogram(values, k=8):
    """Construye k intervalos de igual ancho."""
    # Sin datos o k invalido: no hay histograma.
    data = [float(v) for v in values]
    if not data or k <= 0:
        return []

    minimum = min(data)
    maximum = max(data)

    # Si todos los datos son iguales, hay un solo intervalo.
    if minimum == maximum:
        return [{
            "low": minimum,
            "high": maximum,
            "count": len(data),
        }]

    # Ancho de cada intervalo = rango / k. Creamos los k intervalos vacios.
    width = (maximum - minimum) / k
    bins = []
    for i in range(k):
        low = minimum + i * width
        high = minimum + (i + 1) * width
        bins.append({"low": low, "high": high, "count": 0})

    # Cada dato va al intervalo que le corresponde (el maximo se mete en el ultimo).
    for value in data:
        index = int((value - minimum) / width)
        if index >= k:
            index = k - 1
        bins[index]["count"] += 1

    return bins


# EMBUDO DE PROGRESION: para cada nivel, cuantas partidas lo alcanzaron,
# que porcentaje del total sobrevive y que porcentaje abandona respecto
# al nivel anterior.
def progression(sessions):
    total = len(sessions)
    if total == 0:
        return []

    # Nivel mas alto alcanzado por alguna partida.
    max_level = max(s["max_level"] for s in sessions.values())
    rows = []
    previous = total

    # Para cada nivel de 1 al maximo calculamos los porcentajes.
    for level in range(1, max_level + 1):
        reached = sum(1 for s in sessions.values()
                      if s["max_level"] >= level)
        survival = reached / total if total else 0.0
        abandonment = ((previous - reached) / previous
                        if previous else 0.0)
        rows.append({
            "level": level,
            "sessions": reached,
            "survival": survival,
            "abandonment": None if level == 1 else abandonment,
        })
        previous = reached

    return rows


# CORRELACION DE PEARSON en una sola pasada: solo guarda 6 sumas
# (cantidad, suma x, suma y, suma xy, suma x^2, suma y^2). r va de -1 a 1
# y dice que tanto se mueven juntas dos variables.
class Correlation:
    """Pearson en UN solo recorrido: solo acumula 6 numeros (8.5)."""

    # Las seis sumas empiezan en cero.
    def __init__(self):
        self.n = 0
        self.sx = self.sy = self.sxy = self.sxx = self.syy = 0.0

    # Agrega un par (x, y) actualizando las sumas.
    def add(self, x, y):
        self.n += 1
        self.sx += x
        self.sy += y
        self.sxy += x * y
        self.sxx += x * x
        self.syy += y * y

    # Calcula r con la formula de las sumas. Si hay menos de 2 datos o no hay
    # variacion, devuelve 0.
    def r(self):
        if self.n < 2:
            return 0.0
        numerator = self.n * self.sxy - self.sx * self.sy
        denominator = math.sqrt(max((self.n * self.sxx - self.sx ** 2) *
                                    (self.n * self.syy - self.sy ** 2), 0.0))
        return numerator / denominator if denominator else 0.0


# Atajo: calcula r de dos listas recorriendolas una vez.
def pearson(xs, ys):
    """r de Pearson recorriendo los datos una sola vez."""
    acc = Correlation()
    for x, y in zip(xs, ys):
        acc.add(x, y)
    return acc.r()


# Devuelve las listas x, y (para el grafico de dispersion) y el r.
def correlation_data(sessions, first="duration", second="score"):
    """(xs, ys, r). r sale de las sumas acumuladas; xs e ys se guardan solo
    para dibujar el diagrama de dispersion de la pestana Relacion."""
    acc = Correlation()
    xs, ys = [], []
    for s in sessions.values():
        x, y = float(s.get(first, 0)), float(s.get(second, 0))
        acc.add(x, y)
        xs.append(x)
        ys.append(y)
    return xs, ys, acc.r()


# Traduce r a palabras: muy fuerte / fuerte / moderada / debil / muy debil,
# y positiva, negativa o nula segun el signo.
def correlation_strength(r):
    value = abs(r)
    if value >= 0.90:
        strength = "muy fuerte"
    elif value >= 0.70:
        strength = "fuerte"
    elif value >= 0.50:
        strength = "moderada"
    elif value >= 0.30:
        strength = "debil"
    else:
        strength = "muy debil"

    direction = "positiva" if r > 0 else "negativa" if r < 0 else "nula"
    return "%s y %s" % (strength, direction)


# Orden en que se muestran las dificultades.
DIFFICULTY_ORDER = ("easy", "normal", "hard")


# Compara el puntaje promedio entre easy, normal y hard y calcula la
# diferencia entre hard y easy (en puntos y en porcentaje).
def difficulty_comparison(sessions):
    """Puntaje por dificultad (easy, normal, hard) y diferencia hard-easy."""
    result = {}
    for difficulty in DIFFICULTY_ORDER:
        stats = RunningStats()
        for s in sessions.values():
            if s.get("difficulty") == difficulty:
                stats.add(float(s["score"]))
        result[difficulty] = {
            "n": stats.n,
            "mean": stats.media or 0.0,
            "std": stats.desviacion or 0.0,
        }

    easy_mean = result["easy"]["mean"]
    hard_mean = result["hard"]["mean"]
    difference = hard_mean - easy_mean
    percentage = (difference / easy_mean * 100.0) if easy_mean else 0.0

    result["difference"] = difference
    result["percentage_vs_easy"] = percentage
    return result


# FUNCION PRINCIPAL: hace todo el analisis de la bitacora y devuelve un
# solo diccionario con todos los resultados. La pantalla de estadisticas
# lo usa para dibujar.
def analyze(log_dir):
    sessions = collect_sessions(log_dir)
    values = _numeric_values(sessions)

    return {
        "sessions": sessions,
        "values": values,
        "summary": {
            key: basic_distribution(vals)
            for key, vals in values.items()
        },
        "death_frequency": frequency_table(sessions, "cause"),
        "difficulty_frequency": frequency_table(sessions, "difficulty"),
        "histogram": histogram(values["score"], 8),
        "progression": progression(sessions),
        "difficulty": difficulty_comparison(sessions),
        "correlations": {
            "duration_score": correlation_data(sessions, "duration", "score"),
            "damage_level": correlation_data(sessions, "damage", "level"),
        },
    }