# ======================================================================
# ARCHIVO: tools/report.py - reporte de estadisticas en la terminal
# ======================================================================
# QUE ES: imprime en consola (texto) todas las estadisticas del laboratorio:
# resumen de puntaje/duracion/dano, causas de muerte, histograma, progresion
# por nivel, correlaciones y comparacion por dificultad. Util para copiar los
# numeros al informe sin abrir el juego.
# COMO SE USA:  python tools/report.py [carpeta_de_logs]
# ======================================================================

"""Reporte en consola de las secciones 8.1 a 8.6 sobre la bitacora real.

Uso (desde la raiz del repo):  python tools/report.py [carpeta_logs]
"""
# os: rutas.
import os
# sys: argumentos de la terminal.
import sys

# Raiz del proyecto en la ruta de busqueda de Python.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Traemos el motor de analisis (el mismo que usa el juego).
from game.statistics_engine import analyze, correlation_strength  # noqa: E402


# Funcion principal.
def main():
    # Carpeta de bitacoras: la que se escriba al ejecutar o, si no, 'logs'.
    log_dir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(BASE_DIR, "logs")
    data = analyze(log_dir)
    print("Sesiones completas: %d\n" % len(data["sessions"]))

    # Para puntaje, duracion y dano imprime las medidas en 4 lineas.
    for name in ("score", "duration", "damage"):
        r = data["summary"][name]
        print("== %s ==" % name.upper())
        print("n=%d suma=%.2f min=%.2f max=%.2f rango=%.2f" %
              (r["n"], r["sum"], r["min"], r["max"], r["range"]))
        print("media=%.2f mediana=%.2f desv=%.2f var=%.2f CV=%.2f%%" %
              (r["mean"], r["median"], r["std"], r["variance"], r["cv"]))
        print("Q1=%.2f Q3=%.2f IQR=%.2f P90=%.2f limites=[%.2f, %.2f]" %
              (r["q1"], r["q3"], r["iqr"], r["p90"], r["lower"], r["upper"]))
        print("atipicos IQR=%s  atipicos z>3=%s\n" % (r["outliers"], r["z_outliers"]))

    # Tabla de causas de muerte: frecuencia (f), porcentaje (f%) y acumulado (F%).
    print("CAUSAS DE MUERTE          f      f%      F%")
    for row in data["death_frequency"]:
        print("%-22s %4d %6.1f%% %6.1f%%" % (row["value"], row["frequency"],
              row["relative"] * 100, row["cumulative"] * 100))
    # Total y moda (la causa mas frecuente).
    freq = data["death_frequency"]
    print("Total %d   Moda: %s\n" % (sum(r["frequency"] for r in freq),
                                    freq[0]["value"] if freq else "N/A"))

    # Histograma de texto: cada '#' es una partida en ese intervalo.
    print("HISTOGRAMA DE PUNTAJE (k=8)")
    for b in data["histogram"]:
        print("%9.0f - %9.0f | %s %d" % (b["low"], b["high"], "#" * b["count"], b["count"]))

    # Tabla de progresion: sesiones que llegaron a cada nivel, supervivencia y abandono.
    print("\nNIVEL  SESIONES  SUPERVIVENCIA  ABANDONO")
    for row in data["progression"]:
        ab = "-" if row["abandonment"] is None else "%.1f%%" % (row["abandonment"] * 100)
        print("%5d %9d %13.1f%% %9s" % (row["level"], row["sessions"],
                                        row["survival"] * 100, ab))

    # Correlaciones de Pearson explicadas en palabras.
    for label, key in (("duracion vs puntaje", "duration_score"),
                       ("dano vs nivel", "damage_level")):
        r = data["correlations"][key][2]
        print("\nPearson %s: r = %.5f (%s)" % (label, r, correlation_strength(r)))

    # Comparacion de puntaje entre dificultades easy y hard.
    d = data["difficulty"]
    print()
    for name in ("easy", "hard"):
        print("%s: n=%d media=%.2f desv=%.2f" % (name, d[name]["n"], d[name]["mean"], d[name]["std"]))
    print("Hard - Easy: %+.2f puntos (%+.1f%% respecto a easy)" %
          (d["difference"], d["percentage_vs_easy"]))


# Solo se ejecuta al abrir este archivo directamente.
if __name__ == "__main__":
    main()
