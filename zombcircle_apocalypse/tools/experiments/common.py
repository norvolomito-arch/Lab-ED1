# ======================================================================
# ARCHIVO: tools/experiments/common.py - utilidades de los experimentos
# ======================================================================
# QUE ES: funciones de ayuda que usan los experimentos A, B y C:
# datos de la maquina (CPU, RAM, sistema), mediana, y formatos para mostrar tiempos
# y tamanos legibles. Lo que no se pueda leer queda como 'COMPLETAR'.
# ======================================================================

"""Utilidades compartidas por los experimentos (solo libreria estandar).

- ruta raiz del repo en sys.path
- especificaciones de la maquina (lo que no se puede leer queda "COMPLETAR")
- mediana con sorted (nunca el modulo statistics)
- formatos de texto para tiempos y bytes
"""
# os: rutas y datos del sistema.
import os
# platform: nombre del sistema operativo, procesador y version de Python.
import platform
# sys: ajustar rutas y detectar Windows.
import sys

# Raiz del proyecto en la ruta de Python.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

# Carpeta 'results' donde se guardan graficas y tablas. PENDIENTE: texto
# que marca un dato que debe completar una persona.
RESULTS_DIR = os.path.join(BASE_DIR, "results")
PENDIENTE = "COMPLETAR"


# Mediana usando 'sorted' (no la libreria prohibida 'statistics').
def mediana(valores):
    """Mediana con sorted (promedio de los dos centrales si n es par)."""
    # Ordenamos y tomamos el valor central (o el promedio de los dos centrales).
    orden = sorted(valores)
    n = len(orden)
    if n == 0:
        raise ValueError("lista vacia")
    mid = n // 2
    return orden[mid] if n % 2 else (orden[mid - 1] + orden[mid]) / 2.0


# Intenta leer el nombre del procesador (Linux) o usa platform como alternativa.
def _cpu_modelo():
    try:
        with open("/proc/cpuinfo", "r", encoding="utf-8", errors="replace") as f:
            for linea in f:
                if linea.lower().startswith("model name"):
                    return linea.split(":", 1)[1].strip()
    except OSError:
        pass
    return platform.processor() or PENDIENTE


# Calcula la memoria RAM total en GiB, en Linux/Mac o en Windows.
def _ram_gib():
    """RAM total en GiB, o None si no se puede leer con la libreria estandar."""
    # Linux/Mac: paginas de memoria x tamano de pagina.
    try:
        if hasattr(os, "sysconf") and "SC_PHYS_PAGES" in os.sysconf_names:
            total = os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES")
            return total / 2.0 ** 30
    except (OSError, ValueError):
        pass
    # Windows: se consulta al sistema con ctypes.
    if sys.platform == "win32":
        try:
            import ctypes

            class Estado(ctypes.Structure):
                _fields_ = [("largo", ctypes.c_ulong), ("carga", ctypes.c_ulong),
                            ("total", ctypes.c_ulonglong),
                            ("libre", ctypes.c_ulonglong),
                            ("pag_total", ctypes.c_ulonglong),
                            ("pag_libre", ctypes.c_ulonglong),
                            ("virt_total", ctypes.c_ulonglong),
                            ("virt_libre", ctypes.c_ulonglong),
                            ("ext", ctypes.c_ulonglong)]
            estado = Estado()
            estado.largo = ctypes.sizeof(Estado)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(estado)):
                return estado.total / 2.0 ** 30
        except Exception:
            pass
    return None


# Devuelve la lista de datos de la maquina para el informe. El tipo
# de disco no se puede leer solo: lo debe escribir una persona.
def especificaciones():
    """Lista de (campo, valor) de la maquina. Disco: lo completa la persona."""
    ram = _ram_gib()
    return [
        ("CPU", _cpu_modelo()),
        ("Nucleos logicos", str(os.cpu_count() or PENDIENTE)),
        ("RAM", "%.1f GiB" % ram if ram else PENDIENTE),
        ("Tipo de disco", PENDIENTE + " (SSD NVMe / SSD SATA / HDD)"),
        ("Sistema operativo", "%s %s" % (platform.system(), platform.release())),
        ("Python", platform.python_version()),
    ]


# Convierte la lista de datos en texto, una linea por dato.
def formato_specs(specs):
    return "\n".join("%s: %s" % par for par in specs)


# Formatea segundos con 3 decimales.
def seg(valor):
    """Tiempo en segundos con 3 decimales."""
    return "%.3f s" % valor


# Convierte bytes a B, KiB o MiB segun el tamano.
def bytes_legible(n):
    if n >= 1024 ** 2:
        return "%.2f MiB" % (n / 1024.0 ** 2)
    if n >= 1024:
        return "%.1f KiB" % (n / 1024.0)
    return "%d B" % n
