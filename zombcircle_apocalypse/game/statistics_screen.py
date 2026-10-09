"""
Pantalla de estadisticas de Persona 3.

"""
import os
import pygame

from telemetry import QualityReport, iter_events
from statistics_engine import analyze, correlation_strength


WIDTH = 800
HEIGHT = 600
BG = (20, 22, 30)
TEXT = (235, 235, 235)
MUTED = (160, 165, 175)
ACCENT = (255, 210, 80)
GRID = (70, 75, 90)
BAR = (90, 170, 255)
BAD = (230, 80, 80)


def _fmt(value):
    if isinstance(value, float):
        return "%.2f" % value
    return str(value)


def _draw_text(screen, font, text, x, y, color=TEXT):
    screen.blit(font.render(str(text), True, color), (x, y))


def _scale(value, low, high, start, end):
    if high <= low:
        return (start + end) / 2
    return start + (value - low) / (high - low) * (end - start)


def _draw_axes(screen, rect):
    x, y, w, h = rect
    pygame.draw.line(screen, GRID, (x, y + h), (x + w, y + h), 1)
    pygame.draw.line(screen, GRID, (x, y), (x, y + h), 1)


def _draw_histogram(screen, font, bins, rect):
    x, y, w, h = rect
    if not bins:
        _draw_text(screen, font, "No hay puntajes para graficar.", x, y + 30, MUTED)
        return

    _draw_axes(screen, rect)
    maximum = max(b["count"] for b in bins)
    maximum = max(1, maximum)
    bar_width = w / len(bins)

    for i, item in enumerate(bins):
        bar_h = item["count"] / maximum * (h - 30)
        bx = x + i * bar_width + 2
        by = y + h - bar_h
        pygame.draw.rect(screen, BAR,
                         (int(bx), int(by), int(bar_width - 4), int(bar_h)))
        _draw_text(screen, font, str(item["count"]),
                   int(bx + 4), int(by - 20), TEXT)

    minimum = bins[0]["low"]
    maximum_value = bins[-1]["high"]
    _draw_text(screen, font, "%.0f" % minimum, x, y + h + 5, MUTED)
    label = "%.0f" % maximum_value
    _draw_text(screen, font, label, x + w - 55, y + h + 5, MUTED)


def _draw_boxplot(screen, font, summary, rect):
    x, y, w, h = rect
    if not summary or summary["n"] == 0:
        _draw_text(screen, font, "No hay datos.", x, y + 20, MUTED)
        return

    low = min(summary["min"], summary["lower"])
    high = max(summary["max"], summary["upper"])
    if low == high:
        high = low + 1

    center_y = y + h // 2
    q1x = _scale(summary["q1"], low, high, x + 25, x + w - 25)
    q3x = _scale(summary["q3"], low, high, x + 25, x + w - 25)
    medx = _scale(summary["median"], low, high, x + 25, x + w - 25)
    lowerx = _scale(max(summary["min"], summary["lower"]),
                    low, high, x + 25, x + w - 25)
    upperx = _scale(min(summary["max"], summary["upper"]),
                    low, high, x + 25, x + w - 25)

    pygame.draw.line(screen, TEXT, (int(lowerx), center_y),
                     (int(upperx), center_y), 2)
    pygame.draw.line(screen, TEXT, (int(lowerx), center_y - 12),
                     (int(lowerx), center_y + 12), 2)
    pygame.draw.line(screen, TEXT, (int(upperx), center_y - 12),
                     (int(upperx), center_y + 12), 2)

    pygame.draw.rect(screen, BAR,
                     (int(q1x), center_y - 20,
                      max(2, int(q3x - q1x)), 40), 2)
    pygame.draw.line(screen, ACCENT, (int(medx), center_y - 20),
                     (int(medx), center_y + 20), 3)

    for value in summary["outliers"]:
        ox = _scale(value, low, high, x + 25, x + w - 25)
        pygame.draw.circle(screen, BAD, (int(ox), center_y), 5)

    _draw_text(screen, font, "Q1", int(q1x - 8), center_y + 25, MUTED)
    _draw_text(screen, font, "Med", int(medx - 12), center_y - 42, ACCENT)
    _draw_text(screen, font, "Q3", int(q3x - 8), center_y + 25, MUTED)
    _draw_text(screen, font, "IQR: %.2f" % summary["iqr"], x, y + h - 5, MUTED)


def _draw_scatter(screen, font, xs, ys, r, rect):
    x, y, w, h = rect
    if not xs:
        _draw_text(screen, font, "No hay sesiones suficientes.", x, y + 30, MUTED)
        return

    _draw_axes(screen, rect)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    if xmin == xmax:
        xmax = xmin + 1
    if ymin == ymax:
        ymax = ymin + 1

    for px, py in zip(xs, ys):
        sx = _scale(px, xmin, xmax, x + 30, x + w - 15)
        sy = _scale(py, ymin, ymax, y + h - 25, y + 15)
        pygame.draw.circle(screen, ACCENT, (int(sx), int(sy)), 4)

    _draw_text(screen, font, "x: %.1f - %.1f" % (xmin, xmax),
               x, y + h + 5, MUTED)
    _draw_text(screen, font, "y: %.1f - %.1f" % (ymin, ymax),
               x + 160, y + h + 5, MUTED)
    _draw_text(screen, font, "r = %.5f (%s)" % (r, correlation_strength(r)),
               x, y + h + 25, TEXT)


def _draw_quality(screen, font, report):
    screen.fill(BG)
    _draw_text(screen, pygame.font.Font(None, 42), "CALIDAD DE DATOS", 30, 25)
    lines = report.format().splitlines()
    for i, line in enumerate(lines):
        _draw_text(screen, font, line, 40, 100 + i * 42)
    _draw_text(screen, font, "ESC: volver", 40, 360, MUTED)
    pygame.display.flip()


def _quality_report(log_dir):
    report = QualityReport()
    for _ in iter_events(log_dir, report=report):
        pass
    return report


def run_statistics(screen, log_dir):
    """
    Bucle independiente de la pantalla Statistics.
    ESC vuelve al menu.
    F1 muestra/oculta el panel de calidad.
    """
    try:
        data = analyze(log_dir)
    except Exception as error:
        data = None
        error_text = str(error)

    font = pygame.font.Font(None, 24)
    small = pygame.font.Font(None, 19)
    title = pygame.font.Font(None, 38)

    tab = 0
    variable = 0
    relation = 0
    show_quality = False
    running = True
    clock = pygame.time.Clock()

    variable_names = ("score", "duration", "damage")
    variable_labels = ("PUNTAJE", "DURACION", "DANO")
    relation_labels = (
        ("Duracion", "Puntaje"),
        ("Dano", "Nivel"),
    )

    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_F1:
                    show_quality = not show_quality
                elif event.key in (pygame.K_1, pygame.K_KP1):
                    tab = 0
                elif event.key in (pygame.K_2, pygame.K_KP2):
                    tab = 1
                elif event.key in (pygame.K_3, pygame.K_KP3):
                    tab = 2
                elif event.key == pygame.K_LEFT:
                    if tab == 0:
                        variable = (variable - 1) % 3
                    elif tab == 2:
                        relation = (relation - 1) % 2
                elif event.key == pygame.K_RIGHT:
                    if tab == 0:
                        variable = (variable + 1) % 3
                    elif tab == 2:
                        relation = (relation + 1) % 2

        if show_quality:
            if data is None:
                screen.fill(BG)
                _draw_text(screen, title, "ERROR", 30, 30)
                _draw_text(screen, font, error_text, 30, 100)
            else:
                _draw_quality(screen, font, _quality_report(log_dir))
            for event in pygame.event.get():
                if event.type == pygame.KEYDOWN and event.key == pygame.K_F1:
                    show_quality = False
            clock.tick(30)
            continue

        screen.fill(BG)

        _draw_text(screen, title, "ESTADISTICAS", 25, 18)
        _draw_text(screen, small,
                   "1 Resumen   2 Distribucion   3 Relacion   F1 Calidad   ESC Volver",
                   25, 58, MUTED)

        if data is None:
            _draw_text(screen, font, "Error analizando logs: " + error_text,
                       25, 120, BAD)
            pygame.display.flip()
            clock.tick(30)
            continue

        if tab == 0:
            key = variable_names[variable]
            label = variable_labels[variable]
            summary = data["summary"][key]

            _draw_text(screen, font,
                       "<  %s  >" % label, 25, 100, ACCENT)

            items = [
                ("n", summary["n"]),
                ("Media", "%.2f" % summary["mean"]),
                ("Mediana", "%.2f" % summary["median"]),
                ("Desv. est.", "%.2f" % summary["std"]),
                ("Minimo", "%.2f" % summary["min"]),
                ("Maximo", "%.2f" % summary["max"]),
                ("P90", "%.2f" % summary["p90"]),
                ("IQR", "%.2f" % summary["iqr"]),
            ]

            for i, (name, value) in enumerate(items):
                col = i // 4
                row = i % 4
                _draw_text(screen, font, "%s: %s" % (name, value),
                           50 + col * 300, 155 + row * 48)

            _draw_text(screen, font,
                       "Sesiones completas analizadas: %d" %
                       len(data["sessions"]),
                       50, 370, MUTED)

        elif tab == 1:
            _draw_text(screen, font, "HISTOGRAMA DE PUNTAJES", 25, 100, ACCENT)
            _draw_histogram(screen, small, data["histogram"], (45, 135, 700, 190))

            _draw_text(screen, font, "CAJA Y BIGOTES", 25, 355, ACCENT)
            _draw_boxplot(screen, small, data["summary"]["score"],
                          (45, 385, 700, 100))

            freq = data["death_frequency"]
            mode = freq[0]["value"] if freq else "N/A"
            _draw_text(screen, small, "Moda causa de muerte: " + mode,
                       45, 515, TEXT)

        else:
            first, second = relation_labels[relation]
            _draw_text(screen, font,
                       "<  %s vs %s  >" % (first, second), 25, 100, ACCENT)

            if relation == 0:
                xs, ys, r = data["correlations"]["duration_score"]
                _draw_scatter(screen, small, xs, ys, r,
                              (55, 145, 690, 300))
            else:
                xs, ys, r = data["correlations"]["damage_level"]
                _draw_scatter(screen, small, xs, ys, r,
                              (55, 145, 690, 300))

            diff = data["difficulty"]
            _draw_text(screen, small,
                       "Easy: n=%d, media=%.2f, desv=%.2f" %
                       (diff["easy"]["n"], diff["easy"]["mean"],
                        diff["easy"]["std"]), 55, 500)
            _draw_text(screen, small,
                       "Hard: n=%d, media=%.2f, desv=%.2f" %
                       (diff["hard"]["n"], diff["hard"]["mean"],
                        diff["hard"]["std"]), 55, 525)

        pygame.display.flip()
        clock.tick(30)

    return True
