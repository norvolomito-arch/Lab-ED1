"""
Motor de analisis de Persona 3.

"""
import math
import os

from telemetry import iter_events


def _mean(values):
    if not values:
        return 0.0
    return sum(values) / len(values)


def _sample_std(values):
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    total = sum((x - mean) ** 2 for x in values)
    return math.sqrt(total / (n - 1))


def _median_sorted(values):
    if not values:
        return 0.0
    n = len(values)
    mid = n // 2
    if n % 2:
        return float(values[mid])
    return (values[mid - 1] + values[mid]) / 2.0


def _percentile_sorted(values, p):

    if not values:
        return 0.0
    if len(values) == 1:
        return float(values[0])
    position = (len(values) - 1) * p
    lower = int(position)
    upper = min(lower + 1, len(values) - 1)
    fraction = position - lower
    return values[lower] + (values[upper] - values[lower]) * fraction


def _quartiles(values):

    if not values:
        return 0.0, 0.0, 0.0
    data = sorted(values)
    n = len(data)
    median = _median_sorted(data)
    if n == 1:
        return data[0], data[0], data[0]
    if n % 2 == 0:
        lower = data[:n // 2]
        upper = data[n // 2:]
    else:

        lower = data[:n // 2 + 1]
        upper = data[n // 2:]
    return _median_sorted(lower), median, _median_sorted(upper)


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


def _finish_session(sessions, sid, current):
    if not current:
        return
    sessions[sid] = dict(current)


def collect_sessions(log_dir):

    sessions = {}
    active = {}

    for event in iter_events(log_dir):
        sid = event["session_id"]
        etype = event["event_type"]
        params = event["params"]

        if etype == "SESSION_START":
            state = _new_session()
            state["difficulty"] = params.get("difficulty", "unknown")
            active[sid] = state

        elif sid in active:
            state = active[sid]

            if etype == "DAMAGE_TAKEN":
                state["damage"] += float(params.get("amount", 0))

            elif etype == "PLAYER_DEATH":
                state["cause"] = str(params.get("cause", "unknown"))
                state["level"] = int(params.get("level", state["level"]))
                state["max_level"] = max(state["max_level"], state["level"])

            elif etype == "LEVEL_UP":
                level = int(params.get("level", state["level"]))
                state["level"] = level
                state["max_level"] = max(state["max_level"], level)

            elif etype == "SESSION_END":
                state["score"] = float(params.get("score", 0))
                state["duration"] = float(params.get("duration", 0))
                state["level"] = int(params.get("level", state["level"]))
                state["max_level"] = max(state["max_level"], state["level"])
                state["finished"] = True
                _finish_session(sessions, sid, state)
                del active[sid]

    return sessions


def _numeric_values(sessions):
    return {
        "score": [s["score"] for s in sessions.values()],
        "duration": [s["duration"] for s in sessions.values()],
        "damage": [s["damage"] for s in sessions.values()],
    }


def basic_distribution(values):
    """Datos básicos necesarios para resumen/boxplot."""
    data = sorted(float(v) for v in values)
    if not data:
        return {
            "n": 0, "mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0,
            "median": 0.0, "q1": 0.0, "q3": 0.0, "p90": 0.0,
            "iqr": 0.0, "lower": 0.0, "upper": 0.0, "outliers": []
        }

    q1, median, q3 = _quartiles(data)
    iqr = q3 - q1
    lower = q1 - 1.5 * iqr
    upper = q3 + 1.5 * iqr
    outliers = [x for x in data if x < lower or x > upper]

    return {
        "n": len(data),
        "mean": _mean(data),
        "std": _sample_std(data),
        "min": data[0],
        "max": data[-1],
        "median": median,
        "q1": q1,
        "q3": q3,
        "p90": _percentile_sorted(data, 0.90),
        "iqr": iqr,
        "lower": lower,
        "upper": upper,
        "outliers": outliers,
    }


def frequency_table(sessions, field):
    counts = {}
    for session in sessions.values():
        value = str(session.get(field, "unknown"))
        counts[value] = counts.get(value, 0) + 1

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


def mode_from_frequency(rows):
    return rows[0]["value"] if rows else "N/A"


def histogram(values, k=8):
    """Construye k intervalos de igual ancho."""
    data = [float(v) for v in values]
    if not data or k <= 0:
        return []

    minimum = min(data)
    maximum = max(data)

    if minimum == maximum:
        return [{
            "low": minimum,
            "high": maximum,
            "count": len(data),
        }]

    width = (maximum - minimum) / k
    bins = []
    for i in range(k):
        low = minimum + i * width
        high = minimum + (i + 1) * width
        bins.append({"low": low, "high": high, "count": 0})

    for value in data:
        index = int((value - minimum) / width)
        if index >= k:
            index = k - 1
        bins[index]["count"] += 1

    return bins


def progression(sessions):
    total = len(sessions)
    if total == 0:
        return []

    max_level = max(s["max_level"] for s in sessions.values())
    rows = []
    previous = total

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


def pearson(xs, ys):
    """Coeficiente de Pearson calculado directamente."""
    if len(xs) != len(ys) or len(xs) < 2:
        return 0.0

    n = len(xs)
    sx = sum(xs)
    sy = sum(ys)
    sxy = sum(x * y for x, y in zip(xs, ys))
    sx2 = sum(x * x for x in xs)
    sy2 = sum(y * y for y in ys)

    numerator = n * sxy - sx * sy
    denominator = math.sqrt(
        (n * sx2 - sx * sx) * (n * sy2 - sy * sy)
    )
    if denominator == 0:
        return 0.0
    return numerator / denominator


def correlation_data(sessions, first="duration", second="score"):
    pairs = [
        (float(s.get(first, 0)), float(s.get(second, 0)))
        for s in sessions.values()
    ]
    xs = [p[0] for p in pairs]
    ys = [p[1] for p in pairs]
    return xs, ys, pearson(xs, ys)


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


def difficulty_comparison(sessions):
    result = {}
    for difficulty in ("easy", "hard"):
        values = [
            s["score"] for s in sessions.values()
            if s.get("difficulty") == difficulty
        ]
        result[difficulty] = {
            "n": len(values),
            "mean": _mean(values),
            "std": _sample_std(values),
        }

    easy_mean = result["easy"]["mean"]
    hard_mean = result["hard"]["mean"]
    difference = hard_mean - easy_mean
    percentage = (difference / easy_mean * 100.0) if easy_mean else 0.0

    result["difference"] = difference
    result["percentage_vs_easy"] = percentage
    return result


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
