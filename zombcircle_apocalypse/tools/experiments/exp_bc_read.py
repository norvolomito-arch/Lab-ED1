"""Experimentos B (rendimiento de lectura) y C (lazy vs lista) + tabla resumen.

    python tools/experiments/exp_bc_read.py
    python tools/experiments/exp_bc_read.py --sizes 2000 5000 --reps 2   (prueba rapida)

Para 5 000, 50 000 y 100 000 eventos (mismo seed, mismos eventos de
tools/gen_synthetic_log.py):
  Escritura: tiempo de escribir con el buffer elegido (por defecto el valor de
             BUFFER_SIZE de game/main.py; se imprime cual se uso).
  B:         tiempo de recorrer iter_events con un contador (mediana de REPS),
             eventos/s y microsegundos por linea.
  C:         pico de memoria con tracemalloc (a) recorriendo lazy sin guardar y
             (b) con list(iter_events(...)). tracemalloc se detiene y reinicia
             entre mediciones; no se mezcla con los tiempos (los frena ~4x).
  Disco:     suma de os.path.getsize de todos los events_NNN.log.

Salidas en results/: summary_table.txt, summary_table.tex, exp_b.png, exp_c.png.
"""
import argparse
import gc
import os
import re
import shutil
import sys
import tempfile
import time
import tracemalloc

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import (BASE_DIR, RESULTS_DIR, bytes_legible, especificaciones,
                    formato_specs, mediana)

from telemetry import TelemetryWriter, iter_events
from telemetry.common import list_log_files
from tools.gen_synthetic_log import build_events

SIZES = (5000, 50000, 100000)
MAX_BYTES = 512 * 1024
CABECERA = ["Eventos", "Tamaño archivo", "T. escritura", "T. lectura",
            "Eventos/s", "Mem. perezosa", "Mem. lista"]


def buffer_del_juego():
    """BUFFER_SIZE leido (como texto) de game/main.py; 25 si no se encuentra."""
    ruta = os.path.join(BASE_DIR, "game", "main.py")
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            for linea in f:
                m = re.match(r"\s*BUFFER_SIZE\s*=\s*(\d+)", linea)
                if m:
                    return int(m.group(1))
    except OSError:
        pass
    return 25


def escribir(eventos, carpeta, buffer_size):
    """Escribe los eventos y devuelve segundos (incluye close())."""
    t0 = time.perf_counter()
    with TelemetryWriter(carpeta, buffer_size, MAX_BYTES) as w:
        log = w.log
        for _t, tipo, sid, params in eventos:
            log(tipo, sid, **params)
    return time.perf_counter() - t0


def tamano_en_disco(carpeta):
    return sum(os.path.getsize(p) for p in list_log_files(carpeta))


def contar_lazy(carpeta):
    """Recorre iter_events sin guardar nada; devuelve cuantos eventos hubo."""
    n = 0
    for _ in iter_events(carpeta):
        n += 1
    return n


def tiempo_lectura(carpeta, reps):
    """Mediana (sorted) de ``reps`` recorridos completos; devuelve (seg, n)."""
    tiempos, n = [], 0
    for _ in range(reps):
        t0 = time.perf_counter()
        n = contar_lazy(carpeta)
        tiempos.append(time.perf_counter() - t0)
    return mediana(tiempos), n


def pico_memoria(funcion):
    """Pico (bytes) de tracemalloc al ejecutar ``funcion``; reinicia antes y despues."""
    gc.collect()
    tracemalloc.start()
    tracemalloc.reset_peak()
    try:
        funcion()
        return tracemalloc.get_traced_memory()[1]
    finally:
        tracemalloc.stop()


def medir(n_eventos, seed, buffer_size, reps, tmp_base):
    eventos = build_events(n_eventos, seed)
    carpeta = tempfile.mkdtemp(prefix="expbc_", dir=tmp_base)
    try:
        t_esc = escribir(eventos, carpeta, buffer_size)
        del eventos
        gc.collect()
        disco = tamano_en_disco(carpeta)
        t_lec, n_leidos = tiempo_lectura(carpeta, reps)
        if n_leidos != n_eventos:
            raise RuntimeError("se leyeron %d eventos, se esperaban %d"
                               % (n_leidos, n_eventos))
        mem_lazy = pico_memoria(lambda: contar_lazy(carpeta))
        mem_lista = pico_memoria(lambda: len(list(iter_events(carpeta))))
        return {"eventos": n_eventos, "disco": disco, "t_esc": t_esc,
                "t_lec": t_lec, "eps": n_eventos / t_lec,
                "us_linea": t_lec / n_eventos * 1e6,
                "mem_lazy": mem_lazy, "mem_lista": mem_lista}
    finally:
        shutil.rmtree(carpeta, ignore_errors=True)


def _fila(r):
    return [format(r["eventos"], ","), bytes_legible(r["disco"]),
            "%.3f s" % r["t_esc"], "%.3f s" % r["t_lec"],
            format(int(r["eps"]), ","), bytes_legible(r["mem_lazy"]),
            bytes_legible(r["mem_lista"])]


def tabla_texto(resultados, buffer_size, reps, seed):
    filas = [CABECERA] + [_fila(r) for r in resultados]
    anchos = [max(len(f[i]) for f in filas) for i in range(len(CABECERA))]
    def linea(f):
        return " | ".join(c.rjust(anchos[i]) for i, c in enumerate(f))
    sep = "-+-".join("-" * a for a in anchos)
    out = ["RESUMEN (buffer de escritura = %d, lecturas por tamano = %d, seed = %d)"
           % (buffer_size, reps, seed), "", linea(filas[0]), sep]
    out += [linea(f) for f in filas[1:]]
    out += ["", "DETALLE B (lectura)", "Eventos | T. lectura | Eventos/s | us por linea"]
    for r in resultados:
        out.append("%s | %.3f s | %s | %.2f" % (
            format(r["eventos"], ","), r["t_lec"], format(int(r["eps"]), ","),
            r["us_linea"]))
    out += ["", "DETALLE C (memoria, bytes exactos del pico de tracemalloc)",
            "Eventos | Perezosa | Lista | Lista/Perezosa"]
    for r in resultados:
        out.append("%s | %s | %s | %.1fx" % (
            format(r["eventos"], ","), format(r["mem_lazy"], ","),
            format(r["mem_lista"], ","), r["mem_lista"] / float(r["mem_lazy"])))
    return "\n".join(out)


def tabla_tex(resultados):
    def esc(s):
        return s.replace("%", "\\%").replace("_", "\\_").replace(",", "{,}")
    out = ["\\begin{table}[t]", "\\caption{Resumen de los experimentos de escritura, lectura y memoria.}",
           "\\label{tab:resumen}", "\\centering", "\\footnotesize",
           "\\begin{tabular}{rrrrrrr}", "\\hline",
           " & ".join("\\textbf{%s}" % esc(c) for c in CABECERA) + " \\\\", "\\hline"]
    for r in resultados:
        out.append(" & ".join(esc(c) for c in _fila(r)) + " \\\\")
    out += ["\\hline", "\\end{tabular}", "\\end{table}"]
    return "\n".join(out) + "\n"


def dibujar(resultados, carpeta_out):
    from plotlib import bar_chart
    cats = [format(r["eventos"], ",") for r in resultados]
    bar_chart(os.path.join(carpeta_out, "exp_b.png"),
              "Experimento B: velocidad de lectura con iter_events",
              "Eventos en la bitacora", "Eventos por segundo", cats,
              [("Eventos/s", [r["eps"] for r in resultados])],
              etiquetas=[[format(int(r["eps"]), ",") for r in resultados]])
    kib = lambda b: b / 1024.0
    bar_chart(os.path.join(carpeta_out, "exp_c.png"),
              "Experimento C: pico de memoria, lectura perezosa vs lista",
              "Eventos en la bitacora", "Pico de memoria (KiB, escala log)", cats,
              [("Perezosa (iter_events)", [kib(r["mem_lazy"]) for r in resultados]),
               ("Lista (list(iter_events))", [kib(r["mem_lista"]) for r in resultados])],
              ylog=True,
              etiquetas=[[bytes_legible(r["mem_lazy"]) for r in resultados],
                         [bytes_legible(r["mem_lista"]) for r in resultados]])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--sizes", type=int, nargs="+", default=list(SIZES))
    ap.add_argument("--buffer", type=int, default=None,
                    help="buffer de escritura (por defecto BUFFER_SIZE de game/main.py)")
    ap.add_argument("--reps", type=int, default=5, help="lecturas por tamano")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default=RESULTS_DIR)
    ap.add_argument("--tmp", default=None)
    ap.add_argument("--no-png", action="store_true")
    args = ap.parse_args(argv)

    buffer_size = args.buffer if args.buffer else buffer_del_juego()
    origen = "--buffer" if args.buffer else "game/main.py"
    specs = especificaciones()
    print(formato_specs(specs))
    print("\nBuffer de escritura usado: %d (de %s)" % (buffer_size, origen))
    resultados = []
    for n in args.sizes:
        print("Midiendo %s eventos..." % format(n, ","))
        resultados.append(medir(n, args.seed, buffer_size, args.reps, args.tmp))
    texto = tabla_texto(resultados, buffer_size, args.reps, args.seed)
    os.makedirs(args.out, exist_ok=True)
    with open(os.path.join(args.out, "summary_table.txt"), "w", encoding="utf-8") as f:
        f.write(formato_specs(specs) + "\n\n" + texto + "\n")
    with open(os.path.join(args.out, "summary_table.tex"), "w", encoding="utf-8") as f:
        f.write(tabla_tex(resultados))
    print("\n" + texto)
    if not args.no_png:
        dibujar(resultados, args.out)
        print("\nFiguras: exp_b.png, exp_c.png en " + args.out)
    print("\n>>> PEGAME todo lo impreso (specs + RESUMEN + DETALLE B + DETALLE C) <<<")
    return 0


if __name__ == "__main__":
    sys.exit(main())
