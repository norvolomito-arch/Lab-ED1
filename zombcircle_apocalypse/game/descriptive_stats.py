# ======================================================================
# ARCHIVO: game/descriptive_stats.py - las formulas de estadistica (Persona 2)
# ======================================================================
# QUE ES: el 'cerebro matematico' del laboratorio. Calcula estadisticas SIN usar
# librerias prohibidas (nada de statistics, numpy, pandas ni Counter).
# DOS FAMILIAS DE CALCULO:
#   1) UNA PASADA (clase RunningStats): va recibiendo numeros uno por uno y solo
#      recuerda 5 cosas (cantidad, suma, suma de cuadrados, minimo y maximo).
#      Con eso saca media, varianza, desviacion, CV y rango. Memoria constante.
#   2) NECESITAN ORDENAR (mediana, cuartiles, P90, atipicos): reciben una lista
#      ya ordenada, por eso gastan mas memoria cuanto mas datos haya.
# PALABRAS CLAVE: media = promedio; varianza/desviacion = que tan dispersos estan
# los datos; mediana = el valor del medio; cuartil = corte al 25% o 75%;
# atipico = valor raro, muy lejos del resto.
# ======================================================================

"""
descriptive_stats.py -- Estadisticas descriptivas (8.1) y de orden (8.2).

Solo se usa `math` (permitido). No se usa statistics, numpy, pandas ni Counter.

Hay dos familias de calculos:

  1) UNA PASADA, memoria constante  -> clase RunningStats
     Se alimenta valor por valor con add(x). No guarda los datos: solo
     5 numeros (n, suma, suma de cuadrados, minimo y maximo).

  2) OBLIGAN A GUARDAR Y ORDENAR    -> mediana, cuartiles, P90, atipicos
     Reciben una lista ya ORDENADA. Su memoria crece con n.

Convenciones declaradas (van en el informe):
  - Varianza muestral: se divide entre n - 1.
  - Cuartiles: mediana de cada mitad (si n es impar se excluye la mediana).
  - P90: rango mas cercano, posicion = ceil(p/100 * n).
"""
# math: solo se usa para raiz cuadrada (sqrt) y redondear hacia arriba (ceil).
import math


# ======================================================================
# 8.1  MEDIDAS DESCRIPTIVAS EN UNA SOLA PASADA
# ======================================================================
class RunningStats:
    """Acumula n, suma, suma de cuadrados, minimo y maximo.

    Con esos valores se obtienen media, varianza muestral, desviacion
    estandar, CV y rango SIN haber guardado ningun dato.
    """

    # Todo empieza en cero / vacio.
    def __init__(self):
        self.n = 0
        self.total = 0.0       # suma de x
        self.total_sq = 0.0    # suma de x^2
        self.minimum = None
        self.maximum = None

    # Anota un numero nuevo: cuenta uno mas, lo suma, suma su cuadrado y
    # actualiza el minimo y el maximo si corresponde.
    def add(self, x):
        # n = cuantos numeros llevamos.
        self.n += 1
        self.total += x
        self.total_sq += x * x
        # Si es el primero, o es menor que el minimo actual, es el nuevo minimo.
        if self.minimum is None or x < self.minimum:
            self.minimum = x
        # Igual para el maximo.
        if self.maximum is None or x > self.maximum:
            self.maximum = x

    # RANGO = maximo - minimo (que tan separado esta el extremo bajo del alto).
    @property
    def rango(self):
        # Sin datos no hay rango.
        if self.n == 0:
            return None
        return self.maximum - self.minimum

    # MEDIA = suma / cantidad (el promedio).
    @property
    def media(self):
        if self.n == 0:
            return None
        return self.total / self.n

    # VARIANZA MUESTRAL: mide la dispersion. Formula: (suma de cuadrados - n*media^2) / (n-1).
    # Necesita al menos 2 datos.
    @property
    def varianza_muestral(self):
        # s^2 = (sum(x^2) - n * media^2) / (n - 1)
        if self.n < 2:
            return None
        # Aplicamos la formula. Se divide entre n-1 (y no n) porque son datos de una muestra.
        valor = (self.total_sq - self.n * self.media ** 2) / (self.n - 1)
        return max(valor, 0.0)  # evita -1e-12 por error de redondeo

    # DESVIACION ESTANDAR = raiz de la varianza (esta en las mismas unidades que los datos).
    @property
    def desviacion(self):
        v = self.varianza_muestral
        return None if v is None else math.sqrt(v)

    # CV (coeficiente de variacion) = desviacion / media * 100. Dice la dispersion
    # como porcentaje del promedio. No tiene sentido si la media es 0.
    @property
    def cv_porcentaje(self):
        # CV = desviacion / media * 100 (solo tiene sentido si media != 0)
        d = self.desviacion
        if d is None or self.media == 0:
            return None
        return d / self.media * 100.0

    # Junta todos los resultados en un diccionario, listo para mostrar.
    def resumen(self):
        return {
            "n": self.n,
            "suma": self.total,
            "min": self.minimum,
            "max": self.maximum,
            "rango": self.rango,
            "media": self.media,
            "varianza": self.varianza_muestral,
            "desviacion": self.desviacion,
            "cv": self.cv_porcentaje,
        }


# ======================================================================
# 8.2  MEDIANA, CUARTILES, P90 Y ATIPICOS  (requieren lista ordenada)
# ======================================================================
def mediana(ordenados):
    """Mediana de una lista YA ordenada."""
    n = len(ordenados)
    if n == 0:
        return None
    # '//' es division entera: da la posicion central.
    mitad = n // 2
    if n % 2 == 1:
        return float(ordenados[mitad])
    return (ordenados[mitad - 1] + ordenados[mitad]) / 2.0


# CUARTILES Q1 y Q3: se parte la lista en mitad baja y mitad alta; Q1 es la
# mediana de la mitad baja y Q3 la de la alta. Si la cantidad es impar,
# se deja fuera el valor central. Necesita al menos 2 datos.
def cuartiles(ordenados):
    """(Q1, Q3) con la convencion de MEDIANAS DE LAS MITADES.

    - n par:   Q1 = mediana de la mitad baja, Q3 = mediana de la mitad alta.
    - n impar: se EXCLUYE la mediana y se hace lo mismo con cada lado.

    Es la convencion que reproduce los valores de referencia (Q1=1500, Q3=3000).
    Hay que declararla en el informe.
    """
    n = len(ordenados)
    if n < 2:
        return None, None
    mitad = n // 2
    # Primera mitad de la lista.
    mitad_baja = ordenados[:mitad]
    mitad_alta = ordenados[mitad + (n % 2):]  # si n es impar, salta la mediana
    return mediana(mitad_baja), mediana(mitad_alta)


# PERCENTIL (ej. P90): el valor por debajo del cual queda el p% de los datos.
# Metodo 'rango mas cercano': posicion = redondear hacia arriba(p/100 * n).
def percentil_rango_mas_cercano(ordenados, p):
    """Percentil por 'rango mas cercano' (nearest-rank).

    posicion = ceil(p/100 * n), contada desde 1.
    Para n=10 y p=90: ceil(9.0) = 9 -> ordenados[8] = 3600 (valor de referencia).
    """
    n = len(ordenados)
    if n == 0:
        return None
    # Calculamos la posicion (contando desde 1, por eso luego se resta 1).
    posicion = max(1, math.ceil(p / 100.0 * n))
    return ordenados[posicion - 1]


# IQR = Q3 - Q1 (el ancho de la caja central). Regla de Tukey: un dato es
# atipico si queda a mas de 1.5*IQR por debajo de Q1 o por encima de Q3.
def iqr_y_limites(ordenados):
    """Devuelve (Q1, Q3, IQR, limite_inferior, limite_superior) -- regla de Tukey."""
    q1, q3 = cuartiles(ordenados)
    if q1 is None:
        return None
    iqr = q3 - q1
    return q1, q3, iqr, q1 - 1.5 * iqr, q3 + 1.5 * iqr


# Devuelve los valores atipicos segun la regla del IQR.
def atipicos_iqr(ordenados):
    """Valores fuera de [Q1 - 1.5*IQR, Q3 + 1.5*IQR]."""
    datos = iqr_y_limites(ordenados)
    if datos is None:
        return []
    _, _, _, inferior, superior = datos
    return [x for x in ordenados if x < inferior or x > superior]


# PUNTAJE Z = (x - media) / desviacion: cuantas desviaciones se aleja x
# del promedio.
def puntaje_z(x, media, desviacion):
    if desviacion in (None, 0):
        return None
    return (x - media) / desviacion


# Atipicos por puntaje Z: los que estan a mas de 3 desviaciones del promedio.
# Limitacion: el propio dato raro infla la desviacion y puede 'esconderse'.
def atipicos_z(valores, umbral=3.0):
    """Valores con |z| > umbral. Usa media y desviacion MUESTRAL de la propia lista.

    Ojo (pregunta del informe): el valor sospechoso participa en la media y la
    desviacion, asi que se 'esconde' a si mismo inflando la desviacion.
    """
    # Reutilizamos RunningStats para sacar media y desviacion de la lista.
    stats = RunningStats()
    for x in valores:
        stats.add(x)
    # Si no hay dispersion (o hay muy pocos datos), no hay atipicos.
    if stats.desviacion in (None, 0):
        return []
    # Revisamos dato por dato y guardamos los que superan el umbral.
    resultado = []
    for x in valores:
        z = puntaje_z(x, stats.media, stats.desviacion)
        if abs(z) > umbral:
            resultado.append(x)
    return resultado


# ATAJO: ordena una copia de los datos y devuelve de una vez la mediana, Q1, Q3,
# IQR, P90 y los atipicos (por IQR y por z-score).
def resumen_ordenado(valores):
    """Atajo: ordena una copia y devuelve mediana, Q1, Q3, IQR, P90 y atipicos."""
    ordenados = sorted(valores)
    q1, q3 = cuartiles(ordenados)
    return {
        "mediana": mediana(ordenados),
        "q1": q1,
        "q3": q3,
        "iqr": None if q1 is None else q3 - q1,
        "p90": percentil_rango_mas_cercano(ordenados, 90),
        "atipicos_iqr": atipicos_iqr(ordenados),
        "atipicos_z": atipicos_z(ordenados),
    }