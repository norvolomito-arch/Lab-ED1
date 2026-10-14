# Lab-ED1
Grupo #2. Juego Zombcircle Apocalypse y telemetría para Estructura de Datos I.

## Ejecución

Para jugar localmente, instala `pygame-ce` (se importa como `pygame`):
`python -m pip install pygame-ce`.

```bash
python -m game.main
```

## Ejecutar en el navegador (pygbag)

Requisitos: Python 3.10 a 3.12 (con 3.13 o superior pygbag puede fallar),
internet en la primera carga (el runtime de pygame se descarga de la web) y un
navegador moderno. Ejecuta todo desde la carpeta que contiene `main.py`.

```bash
python -m pip install --upgrade pygbag
python tools/prepare_web.py       # copia a web_stage/ con logs/*.log -> *.txt
python -m pygbag --build web_stage   # genera web_stage/build/web
python -m http.server 8000 --directory web_stage/build/web
```

> **Importante:** pygbag ignora los archivos `.log` al empaquetar, por eso
> `tools/prepare_web.py` renombra `events_NNN.log` a `events_NNN.txt` en la
> copia `web_stage/` (el lector acepta ambas extensiones). Si ejecutas
> `pygbag --build .` directamente, la bitácora NO entra al build y Statistics
> sale vacía.

1. Abre **http://localhost:8000** (no `file://`; en Codespaces abre el puerto
   8000 en la pestaña **Ports**).
2. La primera carga tarda. Con "Ready to start! Please click/touch page",
   haz clic en la página para iniciar el juego.
3. Si se queda cargando: F12 > **Console** para ver el error, recarga sin
   caché (Ctrl+Shift+R) o usa una ventana de incógnito; comprueba que el
   puerto 8000 está libre (`python -m http.server 8001 ...` si no lo está).
4. Para repetir el build desde cero: detén el servidor (Ctrl+C), borra
   `web_stage/` y repite `python tools/prepare_web.py` y `python -m pygbag --build web_stage`.

En el navegador el sistema de archivos es virtual: `config.json` y las
partidas nuevas NO persisten entre recargas (Settings lo avisa en pantalla).
Por eso el build incluye la carpeta `logs/` y el contador
`session_counter.txt` tal como estén en el repo; el juego abre la bitácora en
modo "a" (agrega, no sobrescribe) y la pantalla Statistics la lee. Solo se
usa `assets/music/theme.ogg` en web; el mismo `game/audio.py` sirve en local y
en navegador.

## Icono y música

- Icono: `assets/icon.png` (ventana local) y `favicon.png` (pestaña del
  navegador con pygbag). El logo original está en `assets/logo.jpeg`.
- Música: guarda el archivo como `assets/music/theme.ogg`; ver
  `assets/music/LEEME.md`. Sin archivo, el juego funciona en silencio.

## Pruebas

```bash
python -m unittest discover -s tests -v
```

Las pruebas usan carpetas temporales y no requieren abrir Pygame.

## Bitácora

El juego crea `logs/events_001.log` y rota a `events_002.log`, etc., al superar
512 KiB. Cada línea termina en salto de línea y tiene cuatro campos:
`timestamp|session_id|event_type|clave=valor;clave=valor`.

| Campo | Ejemplo |
| --- | --- |
| timestamp | `1717000012.412` |
| session_id | `S0007` |
| event_type | `SESSION_START` |
| parámetros | `player=ana;difficulty=normal` |

Ejemplo de línea completa:
`1717000012.412|S0007|SESSION_START|player=ana;difficulty=normal`

Los valores se escapan con percent-encoding para que `|`, `;`, `=`, `%` y los
saltos de línea no se confundan con delimitadores. Por ejemplo,
`ana|blue;mode=hard` se guarda como `ana%7Cblue%3Bmode%3Dhard` y el lector lo
reconstruye. Sin escape, un delimitador dentro del valor alteraría los campos
o parámetros y la línea podría descartarse como corrupta. Los valores vacíos
se escriben como `none`.

Para generar la bitácora real, ejecuta el juego, selecciona **Start Game** y
termina cada partida con **Esc**; vuelve al menú y repite al menos 25 veces.
Los archivos quedan en `logs/`. Verifica el total con
`python tools/check_log.py`: con los IDs únicos del juego, debe cumplirse
`Sesiones iniciadas - Sesiones incompletas >= 25` para confirmar 25 partidas
con `SESSION_END`.

Una sesión sin `SESSION_END` se reporta como incompleta y se excluye de los
análisis que requieren el resultado de una partida completa. Quien consuma
`iter_events` puede acumular sus datos por `session_id` y consolidarlos solo
al recibir `SESSION_END`; los eventos siguen disponibles para otros análisis.

Para demostrar tolerancia a corrupción sin alterar el original:
`python tools/inject_corruption.py logs logs_corruptos`, y luego
`python tools/check_log.py logs_corruptos`.

## Generador de bitacoras y experimentos (Partes 6 a 8)

Todo se ejecuta desde la raiz del repo. Las figuras usan solo primitivas de
Pygame (SDL_VIDEODRIVER=dummy); los resultados quedan en `results/`.

    python tools/gen_synthetic_log.py --events 100000 --out carpeta --seed 42
    python tools/gen_synthetic_log.py --sessions 40 --out logs --seed 2024 --overwrite   # demo (borra events_NNN.log de logs/)
    python tools/experiments/exp_a_buffer.py        # Experimento A -> results/exp_a.txt, exp_a.png
    python tools/experiments/exp_bc_read.py         # Experimentos B y C -> summary_table.txt/.tex, exp_b.png, exp_c.png

Los tiempos dependen de la maquina: corre los experimentos en el equipo cuyas
especificaciones iran en el informe y completa el campo "Tipo de disco".
