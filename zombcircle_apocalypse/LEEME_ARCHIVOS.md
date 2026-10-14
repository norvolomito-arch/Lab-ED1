# Guia rapida de archivos (version comentada)

Todos los `.py` empiezan con un recuadro `# ARCHIVO: ...` que explica para que sirve, y cada bloque de codigo tiene comentarios `#` en español sencillo. **Los comentarios no cambian el funcionamiento** (el codigo es identico al de la version limpia; 86/86 pruebas pasan).

| Archivo | Para que sirve |
|---|---|
| `main.py` | Boton de encendido: arranca el juego (lo usa pygbag para la web) |
| `game/main.py` | Director del juego: ventana, menu, pantallas y bucle de 60 FPS |
| `game/game_logic.py` | Reglas: jugador, balas, enemigos, oleadas, niveles y eventos |
| `game/settings_screen.py` | Pantalla Settings y lectura/guardado de `config.json` |
| `game/audio.py` | Musica de fondo |
| `game/descriptive_stats.py` | Formulas de estadistica hechas a mano (Persona 2) |
| `game/statistics_engine.py` | Convierte la bitacora en tablas y numeros (Persona 3) |
| `game/statistics_screen.py` | Dibuja las 3 pestañas de estadisticas y el panel de calidad |
| `telemetry/writer.py` | Escribe la bitacora (buffer, flush, rotacion) |
| `telemetry/reader.py` | Lee la bitacora linea a linea y descarta lineas corruptas |
| `telemetry/quality.py` | Reporte de calidad (validas, corruptas, sesiones incompletas) |
| `telemetry/common.py` | Escape de texto y nombres `events_NNN.log` |
| `tools/` | Utilidades de consola: reporte, generador de datos falsos, experimentos A/B/C |
| `tests/` | 86 pruebas automaticas: `python -m unittest discover -s tests` |

Ejecutar el juego (desde esta carpeta): `python main.py`
