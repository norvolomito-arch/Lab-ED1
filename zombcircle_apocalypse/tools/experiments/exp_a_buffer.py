# ======================================================================
# ARCHIVO: tools/experiments/exp_a_buffer.py - EXPERIMENTO A (tamano del buffer)
# ======================================================================
# QUE ES: un experimento para el informe. Responde: ¿escribir de a muchas lineas
# juntas (buffer grande) es mas rapido que escribir una por una?
# COMO: escribe 100 000 eventos con buffer de 1, 10, 100 y 1000 lineas, mide el
# tiempo de cada uno (varias repeticiones) y guarda una tabla y una grafica en
# la carpeta results/.
# COMO SE USA:  python tools/experiments/exp_a_buffer.py   (tarda unos minutos)
# ======================================================================

"""Experimento A: tiempo de escritura de 100 000 eventos vs tamano de buffer.

    python tools/experiments/exp_a_buffer.py
    python tools/experiments/exp_a_buffer.py --events 20000 --reps 3   (prueba rapida)

Para cada buffer (1, 10, 100, 1000 lineas) escribe los mismos eventos con
TelemetryWriter en una carpeta temporal (se borra al terminar) y mide con
time.perf_counter. Se repite REPS veces por configuracion; las repeticiones se
INTERCALAN entre buffers (1,10,100,1000,1,10,...) para que una deriva de la
maquina (cache de disco, frecuencia de CPU) no favorezca a un buffer.

close() se mide DENTRO del tiempo: el ultimo flush y el cierre del archivo son
trabajo real que el escritor debe hacer para que los datos queden en disco; si
se dejaran fuera, un buffer grande parecería gratis porque tendría lineas
pendientes sin escribir.

Salidas: results/exp_a.txt y results/exp_a.png (primitivas de Pygame).
"""
# Librerias estandar: argparse (opciones de la terminal), os (rutas), shutil
# (borrar carpetas), sys, tempfile (carpetas temporales) y time (cronometro).
import argparse
import os
import shutil
import sys
import tempfile
import time

# Permite importar 'common' que esta en esta misma carpeta.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BASE_DIR, RESULTS_DIR, especificaciones, formato_specs,
                    mediana)

# El escritor real del juego (es lo que se mide) y el generador de eventos falsos.
from telemetry import TelemetryWriter
from tools.gen_synthetic_log import build_events

# Tamanos de buffer a probar y limite de tamano de archivo (igual que el juego).
BUFFERS = (1, 10, 100, 1000)
MAX_BYTES = 512 * 1024      # el mismo umbral de rotacion que el juego


# Mide cuantos segundos tarda escribir todos los eventos con un buffer dado.
# Se usa una carpeta temporal que se borra al terminar. El cierre del escritor
# se incluye en el tiempo (tambien es trabajo real).
def medir_escritura(eventos, buffer_size, max_bytes=MAX_BYTES, tmp_base=None):
    """Segundos para escribir ``eventos`` con ese buffer (incluye close())."""
    # Carpeta temporal para esta medicion.
    carpeta = tempfile.mkdtemp(prefix="expa_", dir=tmp_base)
    try:
        # Cronometro: empieza, se escriben todos los eventos y se calcula la diferencia.
        t0 = time.perf_counter()
        with TelemetryWriter(carpeta, buffer_size, max_bytes) as w:
            log = w.log
            for _t, tipo, sid, params in eventos:
                log(tipo, sid, **params)
        return time.perf_counter() - t0
    # Pase lo que pase, se borra la carpeta temporal.
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


# Repite la medicion varias veces para cada buffer, intercalando
# (1,10,100,1000,1,10...) para que la maquina no favorezca a ninguno.
def ejecutar(eventos, buffers=BUFFERS, reps=5, tmp_base=None):
    """Devuelve {buffer: [tiempos]} con repeticiones intercaladas."""
    tiempos = {b: [] for b in buffers}
    for _ in range(reps):
        for b in buffers:
            tiempos[b].append(medir_escritura(eventos, b, tmp_base=tmp_base))
    return tiempos


# Para cada buffer calcula el tiempo minimo y la mediana.
def resumir(tiempos):
    """Lista de dicts: buffer, minimo, mediana (con sorted)."""
    filas = []
    for b in sorted(tiempos):
        filas.append({"buffer": b, "min": min(tiempos[b]),
                      "mediana": mediana(tiempos[b])})
    return filas


# Arma la tabla en texto: tiempos, eventos por segundo y cuantas veces
# mas rapido es cada buffer que el de 1 linea.
def tabla_texto(filas, n_eventos, tiempos, reps, seed):
    base = filas[0]["mediana"]
    lineas = ["EXPERIMENTO A - tamano de buffer (escritura de %s eventos)"
              % format(n_eventos, ","),
              "Repeticiones por buffer: %d | max_bytes: %d | seed: %d"
              % (reps, MAX_BYTES, seed), "",
              "Buffer | Min (s) | Mediana (s) | Eventos/s (mediana) | Aceleracion vs buffer 1"]
    for f in filas:
        lineas.append("%6d | %7.3f | %11.3f | %19s | %.2fx" % (
            f["buffer"], f["min"], f["mediana"],
            format(int(n_eventos / f["mediana"]), ","), base / f["mediana"]))
    lineas += ["", "Tiempos individuales (s):"]
    for b in sorted(tiempos):
        lineas.append("buffer %d: %s" % (b, ", ".join("%.3f" % t for t in tiempos[b])))
    return "\n".join(lineas)


# Dibuja la grafica de lineas (usa plotlib.py, hecho con primitivas de pygame).
def dibujar(filas, ruta, n_eventos):
    from plotlib import line_chart
    line_chart(ruta,
               "Experimento A: escritura de %s eventos vs tamano de buffer"
               % format(n_eventos, ","),
               "Tamano de buffer (lineas, escala logaritmica)",
               "Tiempo de escritura (s)",
               [f["buffer"] for f in filas],
               [("Mediana", [f["mediana"] for f in filas]),
                ("Minimo", [f["min"] for f in filas])], xlog=True)


# Lee las opciones de la terminal, ejecuta el experimento, imprime la tabla
# y guarda results/exp_a.txt y results/exp_a.png.
def main(argv=None):
    # Opciones: cantidad de eventos, repeticiones, semilla, carpeta de salida...
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--events", type=int, default=100000)
    ap.add_argument("--reps", type=int, default=5)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=RESULTS_DIR)
    ap.add_argument("--tmp", default=None, help="carpeta base de temporales (el disco a medir)")
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args(argv)

    # Primero se muestran los datos de la maquina (CPU, RAM...), necesarios en el informe.
    specs = especificaciones()
    print(formato_specs(specs))
    print("\nGenerando %s eventos en memoria (no se mide)..." % format(args.events, ","))
    # Se generan los eventos en memoria (esto no se cronometra).
    eventos = build_events(args.events, args.seed)
    print("Midiendo (puede tardar unos minutos; el buffer 1 es el mas lento)...")
    # Medimos y resumimos los tiempos.
    tiempos = ejecutar(eventos, reps=args.reps, tmp_base=args.tmp)
    filas = resumir(tiempos)
    texto = tabla_texto(filas, args.events, tiempos, args.reps, args.seed)
    # Guardamos la tabla en results/exp_a.txt.
    os.makedirs(args.out, exist_ok=True)
    ruta_txt = os.path.join(args.out, "exp_a.txt")
    with open(ruta_txt, "w", encoding="utf-8") as f:
        f.write(formato_specs(specs) + "\n\n" + texto + "\n")
    print("\n" + texto)
    # Guardamos la grafica (a menos que se pida no hacerla).
    if not args.no_png:
        ruta_png = os.path.join(args.out, "exp_a.png")
        dibujar(filas, ruta_png, args.events)
        print("\nFigura: " + ruta_png)
    print("Tabla: " + ruta_txt)
    print("\n>>> PEGAME todo lo impreso (specs + tabla + tiempos individuales) <<<")
    return 0


# Solo se ejecuta al abrir el archivo directamente.
if __name__ == "__main__":
    sys.exit(main())
