# ======================================================================
# ARCHIVO: tools/experiments/plotlib.py - dibuja las graficas de los experimentos
# ======================================================================
# QUE ES: una mini-libreria para dibujar graficas (lineas y barras) y guardarlas
# como imagen PNG. Esta hecha SOLO con pygame (lineas, rectangulos, circulos y
# texto) porque el laboratorio prohibe matplotlib/plotly.
# Funciona sin abrir ventana (modo 'dummy' de pygame).
# ======================================================================

"""Figuras de los experimentos dibujadas SOLO con primitivas de Pygame.

Usa draw.rect / draw.line / draw.circle y texto; se guarda con
pygame.image.save sobre una Surface (SDL_VIDEODRIVER=dummy, sin ventana).
Dos graficas: line_chart (eje x logaritmico opcional) y bar_chart (eje y
logaritmico opcional). Funciones puras de escala: nice_ticks, log_ticks.
"""
# math: logaritmos y redondeos para calcular las escalas.
import math
# os: variables de entorno y carpetas.
import os

# Le dice a pygame que no abra ventana (dibuja en memoria) y que no
# imprima su mensaje de bienvenida.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("PYGAME_HIDE_SUPPORT_PROMPT", "1")

# Tamano de la imagen (900x560) y margenes alrededor del grafico.
W, H = 900, 560
MARGIN = {"left": 100, "right": 40, "top": 60, "bottom": 85}
# Colores (R, G, B) usados: negro, gris, gris claro, blanco y una paleta para las series.
NEGRO, GRIS, GRIS_CLARO = (20, 20, 20), (120, 120, 120), (225, 225, 225)
BLANCO = (255, 255, 255)
COLORES = [(31, 119, 180), (214, 39, 40), (44, 160, 44), (255, 127, 14)]


# Escoge marcas 'redondas' para el eje (1, 2, 5, 10 x potencias de 10)
# que cubran de 'lo' a 'hi', como 0, 20, 40, 60...
def nice_ticks(lo, hi, n=6):
    """Marcas 'redondas' (1, 2, 5 x 10^k) que cubren [lo, hi]; lo suele ser 0."""
    if hi <= lo:
        hi = lo + 1.0
    crudo = (hi - lo) / float(max(1, n - 1))
    pot = 10 ** math.floor(math.log10(crudo))
    paso = pot
    for mult in (1, 2, 5, 10):
        paso = mult * pot
        if paso >= crudo:
            break
    ini = math.floor(lo / paso) * paso
    marcas = []
    v = ini
    while v < hi + paso * 0.999:
        marcas.append(round(v, 12))
        v += paso
    return marcas


# Marcas para un eje logaritmico: potencias de 10 (1, 10, 100...).
def log_ticks(lo, hi):
    """Potencias de 10 que cubren [lo, hi] (lo > 0)."""
    a = int(math.floor(math.log10(lo)))
    b = int(math.ceil(math.log10(hi)))
    if b == a:
        b += 1
    return [10.0 ** k for k in range(a, b + 1)]


# Da formato corto a un numero para mostrarlo en el grafico.
def fmt_num(v):
    if v == 0:
        return "0"
    if abs(v) >= 1000 and float(v).is_integer():
        return format(int(v), ",")
    if abs(v) >= 100:
        return "%.0f" % v
    if abs(v) >= 1:
        return ("%.2f" % v).rstrip("0").rstrip(".")
    return ("%.3f" % v).rstrip("0").rstrip(".")


# LIENZO: la 'hoja de papel' donde se dibuja: superficie, margenes, ejes y
# conversion de valores a pixeles.
class _Lienzo:
    """Superficie + zona de trazado + conversion de datos a pixeles."""

    # Crea la hoja blanca, las fuentes y escribe el titulo y los nombres de los ejes
    # (el del eje vertical se gira 90 grados).
    def __init__(self, titulo, xlabel, ylabel):
        import pygame
        self.pg = pygame
        pygame.font.init()
        self.surf = pygame.Surface((W, H))
        self.surf.fill(BLANCO)
        self.f_tit = pygame.font.Font(None, 30)
        self.f_eje = pygame.font.Font(None, 24)
        self.f_marca = pygame.font.Font(None, 22)
        self.x0 = MARGIN["left"]
        self.x1 = W - MARGIN["right"]
        self.y0 = H - MARGIN["bottom"]      # eje x (abajo)
        self.y1 = MARGIN["top"]             # tope
        self.texto(titulo, W // 2, 22, self.f_tit, centro=True)
        self.texto(xlabel, (self.x0 + self.x1) // 2, H - 22, self.f_eje, centro=True)
        rot = self.f_eje.render(ylabel, True, NEGRO)
        rot = pygame.transform.rotate(rot, 90)
        self.surf.blit(rot, (18, (self.y0 + self.y1) // 2 - rot.get_height() // 2))

    # Escribe texto en (x, y), alineado al centro, a la derecha o a la izquierda.
    def texto(self, s, x, y, fuente, centro=False, derecha=False, color=NEGRO):
        img = fuente.render(s, True, color)
        if centro:
            x -= img.get_width() // 2
        elif derecha:
            x -= img.get_width()
        self.surf.blit(img, (x, y))

    # Convierte una posicion relativa 0-1 a pixel horizontal.
    def px(self, t):             # t en [0,1] -> pixel x
        return int(self.x0 + t * (self.x1 - self.x0))

    # Convierte una posicion relativa 0-1 a pixel vertical (0 abajo, 1 arriba).
    def py(self, t):             # t en [0,1] -> pixel y
        return int(self.y0 - t * (self.y0 - self.y1))

    # Dibuja los dos ejes.
    def marco(self):
        pg = self.pg
        pg.draw.line(self.surf, NEGRO, (self.x0, self.y0), (self.x1, self.y0), 2)
        pg.draw.line(self.surf, NEGRO, (self.x0, self.y0), (self.x0, self.y1), 2)

    # Dibuja una marca del eje vertical con su linea de rejilla y su numero.
    def marca_y(self, t, etiqueta):
        y = self.py(t)
        self.pg.draw.line(self.surf, GRIS_CLARO, (self.x0, y), (self.x1, y), 1)
        self.pg.draw.line(self.surf, NEGRO, (self.x0 - 5, y), (self.x0, y), 2)
        self.texto(etiqueta, self.x0 - 9, y - 7, self.f_marca, derecha=True)

    # Dibuja una marca del eje horizontal con su linea de rejilla y su etiqueta.
    def marca_x(self, t, etiqueta):
        x = self.px(t)
        self.pg.draw.line(self.surf, GRIS_CLARO, (x, self.y0), (x, self.y1), 1)
        self.pg.draw.line(self.surf, NEGRO, (x, self.y0), (x, self.y0 + 5), 2)
        self.texto(etiqueta, x, self.y0 + 9, self.f_marca, centro=True)

    # Dibuja el cuadro de leyenda (que color es cada serie).
    def leyenda(self, nombres):
        x, y = self.x0 + 14, self.y1 + 10
        ancho = 40 + max(self.f_marca.size(n)[0] for n in nombres) + 14
        alto = 12 + 22 * len(nombres)
        self.pg.draw.rect(self.surf, BLANCO, (x - 8, y - 6, ancho, alto))
        self.pg.draw.rect(self.surf, GRIS, (x - 8, y - 6, ancho, alto), 1)
        for i, nombre in enumerate(nombres):
            c = COLORES[i % len(COLORES)]
            yy = y + 22 * i + 6
            self.pg.draw.line(self.surf, c, (x, yy), (x + 26, yy), 3)
            self.pg.draw.circle(self.surf, c, (x + 13, yy), 5)
            self.texto(nombre, x + 34, yy - 7, self.f_marca)

    # Crea la carpeta si hace falta y guarda la imagen como archivo.
    def guardar(self, ruta):
        carpeta = os.path.dirname(ruta)
        if carpeta:
            os.makedirs(carpeta, exist_ok=True)
        self.pg.image.save(self.surf, ruta)


# GRAFICA DE LINEAS con puntos: cada serie es una linea; el eje x puede ser
# logaritmico. Cada punto muestra su valor.
def line_chart(ruta, titulo, xlabel, ylabel, xs, series, xlog=True):
    """Lineas con marcadores. series = [(nombre, [y...])], un valor por x.

    Eje x logaritmico (las marcas son los propios valores de xs); eje y
    lineal desde 0 con marcas redondas. Cada punto lleva su valor.
    """
    lienzo = _Lienzo(titulo, xlabel, ylabel)
    # Escala vertical: de 0 al maximo con marcas redondas.
    ymax = max(max(ys) for _, ys in series)
    yt = nice_ticks(0.0, ymax * 1.08)
    ytop = yt[-1]
    lienzo.marco()
    for v in yt:
        lienzo.marca_y(v / ytop, fmt_num(v))
    # Funciones que convierten x a posicion relativa (con un pequeno margen
    # para que los extremos no queden pegados al eje).
    lo, hi = math.log10(xs[0]), math.log10(xs[-1])

    def tx(x):
        if xlog:
            return (math.log10(x) - lo) / (hi - lo) if hi > lo else 0.5
        return (x - xs[0]) / float(xs[-1] - xs[0]) if xs[-1] > xs[0] else 0.5
    # Margen interno para que los extremos no queden sobre el eje.
    def tx_pad(x):
        return 0.04 + 0.92 * tx(x)
    # Marcas del eje x.
    for x in xs:
        lienzo.marca_x(tx_pad(x), fmt_num(x))
    # Dibujamos cada serie: lineas entre puntos, circulos y el valor sobre cada punto.
    for i, (nombre, ys) in enumerate(series):
        c = COLORES[i % len(COLORES)]
        pts = [(lienzo.px(tx_pad(x)), lienzo.py(y / ytop)) for x, y in zip(xs, ys)]
        if len(pts) > 1:
            lienzo.pg.draw.lines(lienzo.surf, c, False, pts, 3)
        for (px_, py_), y in zip(pts, ys):
            lienzo.pg.draw.circle(lienzo.surf, c, (px_, py_), 6)
            # Serie 0 arriba del punto, las demas debajo: sin pisar marcadores.
            dy = -26 if i == 0 else 10 + 16 * (i - 1)
            lienzo.texto(fmt_num(round(y, 3)), px_, py_ + dy,
                         lienzo.f_marca, centro=True, color=c)
    lienzo.leyenda([n for n, _ in series])
    lienzo.guardar(ruta)


# GRAFICA DE BARRAS agrupadas por categoria; el eje y puede ser logaritmico.
def bar_chart(ruta, titulo, xlabel, ylabel, categorias, series, ylog=False,
              etiquetas=None):
    """Barras agrupadas. series = [(nombre, [valor por categoria])].

    ylog=True: eje y logaritmico (potencias de 10). ``etiquetas`` opcional:
    lista de listas con el texto sobre cada barra (mismo orden que series).
    """
    lienzo = _Lienzo(titulo, xlabel, ylabel)
    # Escala vertical (logaritmica o normal) segun la opcion elegida.
    todos = [v for _, vs in series for v in vs]
    lienzo.marco()
    if ylog:
        marcas = log_ticks(min(todos), max(todos))
        lo, hi = math.log10(marcas[0]), math.log10(marcas[-1])

        def ty(v):
            return (math.log10(max(v, marcas[0])) - lo) / (hi - lo)
        for m in marcas:
            lienzo.marca_y(ty(m), fmt_num(m))
    else:
        marcas = nice_ticks(0.0, max(todos) * 1.08)

        def ty(v):
            return v / marcas[-1]
        for m in marcas:
            lienzo.marca_y(ty(m), fmt_num(m))
    # Calculamos el ancho de cada grupo y de cada barra.
    n_cat, n_ser = len(categorias), len(series)
    ancho_grupo = (lienzo.x1 - lienzo.x0) / float(n_cat)
    ancho_barra = ancho_grupo * 0.7 / n_ser
    # Para cada categoria: su nombre debajo y una barra por serie con su valor encima.
    for j, cat in enumerate(categorias):
        gx = lienzo.x0 + ancho_grupo * j
        lienzo.texto(str(cat), int(gx + ancho_grupo / 2), lienzo.y0 + 9,
                     lienzo.f_marca, centro=True)
        for i, (nombre, valores) in enumerate(series):
            c = COLORES[i % len(COLORES)]
            bx = gx + ancho_grupo * 0.15 + ancho_barra * i
            ytop = lienzo.py(ty(valores[j]))
            lienzo.pg.draw.rect(lienzo.surf, c, (int(bx), ytop, int(ancho_barra) - 2,
                                                 lienzo.y0 - ytop))
            texto = etiquetas[i][j] if etiquetas else fmt_num(round(valores[j], 2))
            lienzo.texto(texto, int(bx + ancho_barra / 2), ytop - 18,
                         lienzo.f_marca, centro=True)
    # Si hay varias series, mostramos la leyenda y guardamos la imagen.
    if n_ser > 1:
        lienzo.leyenda([n for n, _ in series])
    lienzo.guardar(ruta)
