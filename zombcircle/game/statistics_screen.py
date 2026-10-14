# ======================================================================
# ARCHIVO: game/statistics_screen.py - la PANTALLA de estadisticas (Persona 3)
# ======================================================================
# QUE ES: dibuja las estadisticas en la ventana. Tiene 3 pestanas:
#   1 = Resumen (tabla de numeros: media, mediana, varianza, etc.)
#   2 = Distribucion (histograma + diagrama de caja y bigotes)
#   3 = Relacion (grafico de puntos con la correlacion r + comparacion por dificultad)
# TECLAS: 1/2/3 cambian de pestana, flechas izquierda/derecha cambian de variable,
# F1 muestra el panel de calidad de datos, ESC vuelve al menu.
# Los calculos los hace statistics_engine.py; aqui solo se dibuja con pygame.
# ======================================================================

"""
Pantalla de estadisticas de Persona 3.

"""
# asyncio: para ceder el control al navegador en cada fotograma (pygbag).
import asyncio

# pygame: dibujar lineas, rectangulos, circulos y texto.
import pygame

# Traemos el analisis de datos y dos funciones de ayuda.
from game.statistics_engine import analyze, correlation_strength, mode_from_frequency
# Reporte de calidad y lector de la bitacora.
from telemetry import QualityReport, iter_events

# COLORES (R, G, B): fondo, texto, texto apagado, resaltado, rejilla,
# barras y color de 'malo' (rojo, para atipicos y errores).
BG = (20, 22, 30)
TEXT = (235, 235, 235)
MUTED = (160, 165, 175)
ACCENT = (255, 210, 80)
GRID = (70, 75, 90)
BAR = (90, 170, 255)
BAD = (230, 80, 80)


# Ayudante: escribe un texto en la posicion (x, y).
def _draw_text(screen, font, text, x, y, color=TEXT):
    screen.blit(font.render(str(text), True, color), (x, y))


# Ayudante: convierte un valor de datos a una posicion en pantalla
# (una 'regla de tres'). Ej.: el dato minimo va al borde izquierdo del
# grafico y el maximo al derecho.
def _scale(value, low, high, start, end):
    if high <= low:
        return (start + end) / 2
    return start + (value - low) / (high - low) * (end - start)


# Dibuja los dos ejes (linea horizontal abajo y vertical a la izquierda).
def _draw_axes(screen, rect):
    x, y, w, h = rect
    pygame.draw.line(screen, GRID, (x, y + h), (x + w, y + h), 1)
    pygame.draw.line(screen, GRID, (x, y), (x, y + h), 1)


# Dice entre que pixeles se dibuja en horizontal. El histograma y la caja
# usan EL MISMO rango para que queden alineados.
def _h_range(rect):
    """Rango horizontal en pixeles. Histograma y caja usan EL MISMO rango (9)."""
    x, _, w, _ = rect
    return x + 40, x + w - 15


# Dibuja 5 marcas con numeros bajo el eje horizontal, del minimo al maximo.
def _draw_x_ticks(screen, font, rect, low, high, label):
    """Marcas del eje horizontal (5 valores entre el minimo y el maximo)."""
    x, y, w, h = rect
    px0, px1 = _h_range(rect)
    for i in range(5):
        tx = int(px0 + (px1 - px0) * i / 4)
        pygame.draw.line(screen, GRID, (tx, y + h), (tx, y + h + 4), 1)
        _draw_text(screen, font, "%.0f" % (low + (high - low) * i / 4),
                   tx - 14, y + h + 6, MUTED)
    _draw_text(screen, font, label, px1 - 40, y + h + 22, MUTED)


# Dibuja el HISTOGRAMA: una barra por intervalo, tan alta como la
# cantidad de partidas que caen ahi, con el numero encima.
def _draw_histogram(screen, font, bins, rect):
    x, y, w, h = rect
    if not bins:
        _draw_text(screen, font, "No hay puntajes para graficar.", x, y + 30, MUTED)
        return

    _draw_axes(screen, rect)
    px0, px1 = _h_range(rect)
    # La barra mas alta define la escala vertical.
    top = max(1, max(b["count"] for b in bins))
    bar_width = (px1 - px0) / len(bins)

    for i, item in enumerate(bins):
        bar_h = item["count"] / top * (h - 30)
        bx = px0 + i * bar_width
        by = y + h - bar_h
        pygame.draw.rect(screen, BAR,
                         (int(bx) + 1, int(by), max(1, int(bar_width) - 2), int(bar_h)))
        _draw_text(screen, font, str(item["count"]), int(bx + 4), int(by - 18), TEXT)

    _draw_text(screen, font, "Frecuencia", x, y - 2, MUTED)
    _draw_x_ticks(screen, font, rect, bins[0]["low"], bins[-1]["high"], "Puntaje")


# Dibuja el DIAGRAMA DE CAJA Y BIGOTES: la caja va de Q1 a Q3, la raya
# amarilla es la mediana, los bigotes llegan a los limites sin atipicos
# y los puntos rojos son los valores atipicos.
def _draw_boxplot(screen, font, summary, rect):
    x, y, w, h = rect
    if not summary or summary["n"] == 0:
        _draw_text(screen, font, "No hay datos.", x, y + 20, MUTED)
        return

    px0, px1 = _h_range(rect)
    low, high = summary["min"], summary["max"]   # mismo rango que el histograma
    center_y = y + h // 2

    # Convierte un valor a posicion horizontal con la misma escala del histograma.
    def pos(value):
        return int(_scale(value, low, high, px0, px1))

    # Posiciones en pantalla de los limites, Q1, Q3 y mediana.
    lowerx = pos(max(low, summary["lower"]))
    upperx = pos(min(high, summary["upper"]))
    q1x, q3x, medx = pos(summary["q1"]), pos(summary["q3"]), pos(summary["median"])

    pygame.draw.line(screen, TEXT, (lowerx, center_y), (upperx, center_y), 2)
    pygame.draw.line(screen, TEXT, (lowerx, center_y - 12), (lowerx, center_y + 12), 2)
    pygame.draw.line(screen, TEXT, (upperx, center_y - 12), (upperx, center_y + 12), 2)
    pygame.draw.rect(screen, BAR, (q1x, center_y - 20, max(2, q3x - q1x), 40), 2)
    pygame.draw.line(screen, ACCENT, (medx, center_y - 20), (medx, center_y + 20), 3)

    # Cada atipico se pinta como un punto rojo.
    for value in summary["outliers"]:
        pygame.draw.circle(screen, BAD, (pos(value), center_y), 5)

    _draw_text(screen, font, "Q1", q1x - 8, center_y + 25, MUTED)
    _draw_text(screen, font, "Med", medx - 12, center_y - 42, ACCENT)
    _draw_text(screen, font, "Q3", q3x - 8, center_y + 25, MUTED)
    _draw_text(screen, font, "IQR: %.2f" % summary["iqr"], x, y + h - 5, MUTED)


# Dibuja el DIAGRAMA DE DISPERSION: un punto por partida (x contra y) y
# debajo el valor de r con su descripcion en palabras.
def _draw_scatter(screen, font, xs, ys, r, rect):
    x, y, w, h = rect
    if not xs:
        _draw_text(screen, font, "No hay sesiones suficientes.", x, y + 30, MUTED)
        return

    _draw_axes(screen, rect)
    # Rangos de x e y; si todos son iguales se agrega 1 para no dividir entre 0.
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)

    if xmin == xmax:
        xmax = xmin + 1
    if ymin == ymax:
        ymax = ymin + 1

    # Cada partida es un punto amarillo.
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


# Dibuja el PANEL DE CALIDAD (tecla F1): archivos, lineas leidas, validas,
# corruptas y sesiones incompletas.
def _draw_quality(screen, font, report):
    screen.fill(BG)
    _draw_text(screen, pygame.font.Font(None, 42), "CALIDAD DE DATOS", 30, 25)
    lines = report.format().splitlines()
    for i, line in enumerate(lines):
        _draw_text(screen, font, line, 40, 100 + i * 42)
    _draw_text(screen, font, "ESC: volver", 40, 360, MUTED)
    pygame.display.flip()


# Recorre la bitacora solo para contar (no guarda eventos) y devuelve el reporte.
def _quality_report(log_dir):
    report = QualityReport()
    for _ in iter_events(log_dir, report=report):
        pass
    return report


# FUNCION PRINCIPAL de la pantalla. Es un bucle propio que se repite hasta
# que el usuario presiona ESC (devuelve True) o cierra la ventana (False).
async def run_statistics(screen, log_dir):
    """
    Bucle independiente de la pantalla Statistics.
    ESC vuelve al menu.
    F1 muestra/oculta el panel de calidad.
    """
    # Primero se hace todo el analisis. Si algo falla, se guarda el error
    # para mostrarlo en pantalla en vez de cerrar el juego.
    try:
        data = analyze(log_dir)
    except Exception as error:
        data = None
        error_text = str(error)

    # Tres tamanos de letra.
    font = pygame.font.Font(None, 24)
    small = pygame.font.Font(None, 19)
    title = pygame.font.Font(None, 38)

    # Estado de la pantalla: pestana actual, variable elegida, par de variables
    # de la pestana 3 y si se muestra el panel de calidad.
    tab = 0
    variable = 0
    relation = 0
    show_quality = False
    running = True
    clock = pygame.time.Clock()

    # Nombres internos y rotulos de las variables y los pares de la pestana 3.
    variable_names = ("score", "duration", "damage")
    variable_labels = ("PUNTAJE", "DURACION", "DAÑO")
    relation_labels = (
        ("Duracion", "Puntaje"),
        ("Daño", "Nivel"),
    )

    # BUCLE: se repite hasta salir.
    while running:
        # Leer teclado: ESC sale, F1 abre/cierra calidad, 1/2/3 cambian pestana,
        # flechas izquierda/derecha cambian de variable.
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

        # Si el panel de calidad esta activo, se dibuja solo ese panel y se
        # espera ESC o F1 para cerrarlo.
        if show_quality:
            if data is None:
                screen.fill(BG)
                _draw_text(screen, title, "ERROR", 30, 30)
                _draw_text(screen, font, error_text, 30, 100)
            else:
                _draw_quality(screen, font, _quality_report(log_dir))
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    return False
                if event.type == pygame.KEYDOWN and event.key in (
                        pygame.K_F1, pygame.K_ESCAPE):
                    show_quality = False  # ESC tambien cierra el panel de calidad
            clock.tick(30)
            await asyncio.sleep(0)  # cede el control (requisito de pygbag)
            continue

        screen.fill(BG)

        # Pintamos el fondo y los titulos de la pantalla.
        _draw_text(screen, title, "ESTADISTICAS", 25, 18)
        _draw_text(screen, small,
                   "1 Resumen   2 Distribucion   3 Relacion   F1 Calidad   ESC Volver",
                   25, 58, MUTED)

        # Si el analisis fallo, mostramos el error y seguimos.
        if data is None:
            _draw_text(screen, font, "Error analizando logs: " + error_text,
                       25, 120, BAD)
            pygame.display.flip()
            clock.tick(30)
            await asyncio.sleep(0)  # cede el control (requisito de pygbag)
            continue

        # PESTANA 1 - RESUMEN: elegimos la variable y mostramos 12 medidas
        # en 3 columnas, mas cuantas partidas se analizaron.
        if tab == 0:
            key = variable_names[variable]
            label = variable_labels[variable]
            summary = data["summary"][key]

            _draw_text(screen, font,
                       "<  %s  >" % label, 25, 100, ACCENT)

            # Lista de (nombre, valor) que se va a mostrar.
            items = [
                ("n", summary["n"]),
                ("Suma", "%.2f" % summary["sum"]),
                ("Rango", "%.2f" % summary["range"]),
                ("Varianza", "%.2f" % summary["variance"]),
                ("Minimo", "%.2f" % summary["min"]),
                ("Maximo", "%.2f" % summary["max"]),
                ("Media", "%.2f" % summary["mean"]),
                ("Mediana", "%.2f" % summary["median"]),
                ("Desv. est.", "%.2f" % summary["std"]),
                ("CV", "%.2f %%" % summary["cv"]),
                ("P90", "%.2f" % summary["p90"]),
                ("IQR", "%.2f" % summary["iqr"]),
            ]

            for i, (name, value) in enumerate(items):
                col = i // 4
                row = i % 4
                _draw_text(screen, font, "%s: %s" % (name, value),
                           50 + col * 260, 155 + row * 48)

            _draw_text(screen, font,
                       "Sesiones completas analizadas: %d" %
                       len(data["sessions"]),
                       50, 370, MUTED)

        # PESTANA 2 - DISTRIBUCION: histograma de puntajes, caja y bigotes del
        # puntaje, y la moda de la causa de muerte.
        elif tab == 1:
            _draw_text(screen, font, "HISTOGRAMA DE PUNTAJES", 25, 100, ACCENT)
            _draw_histogram(screen, small, data["histogram"], (45, 135, 700, 190))

            _draw_text(screen, font, "CAJA Y BIGOTES", 25, 355, ACCENT)
            _draw_boxplot(screen, small, data["summary"]["score"],
                          (45, 385, 700, 100))

            freq = data["death_frequency"]
            _draw_text(screen, small,
                       "Moda causa de muerte: " + mode_from_frequency(freq),
                       45, 515, TEXT)

        # PESTANA 3 - RELACION: grafico de dispersion de la pareja elegida
        # (duracion-puntaje o dano-nivel) y comparacion de puntajes por dificultad.
        else:
            first, second = relation_labels[relation]
            _draw_text(screen, font,
                       "<  %s vs %s  >" % (first, second), 25, 100, ACCENT)

            if relation == 0:
                xs, ys, r = data["correlations"]["duration_score"]
                _draw_scatter(screen, small, xs, ys, r,
                              (55, 145, 690, 270))
            else:
                xs, ys, r = data["correlations"]["damage_level"]
                _draw_scatter(screen, small, xs, ys, r,
                              (55, 145, 690, 270))

            # Una linea por dificultad (n, media, desviacion) y la diferencia hard-easy.
            diff = data["difficulty"]
            for row, name in enumerate(("easy", "normal", "hard")):
                _draw_text(screen, small,
                           "%s: n=%d, media=%.2f, desv=%.2f" %
                           (name.capitalize(), diff[name]["n"],
                            diff[name]["mean"], diff[name]["std"]),
                           55, 490 + 22 * row)
            _draw_text(screen, small,
                       "Hard - Easy: %+.2f puntos (%+.1f%% respecto a easy)" %
                       (diff["difference"], diff["percentage_vs_easy"]),
                       55, 556)

        pygame.display.flip()
        clock.tick(30)
        await asyncio.sleep(0)  # cede el control (requisito de pygbag)

    # Al salir del bucle devolvemos True (volver al menu).
    return True