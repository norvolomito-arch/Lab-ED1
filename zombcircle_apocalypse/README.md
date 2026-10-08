# Lab-ED1
Grupo #2. Juego Zombcircle Apocalypse y telemetría para Estructura de Datos I.

## Ejecución

Para jugar localmente, instala `pygame-ce` (se importa como `pygame`):
`python -m pip install pygame-ce`.

```bash
python -m game.main
```

## Ejecutar en el navegador (pygbag)

Requisitos: Python 3.10-3.12 recomendado, conexión a internet (pygbag descarga
el runtime de pygame desde internet la primera vez) y un navegador moderno.

```bash
python -m pip install --upgrade pygbag
   cd /workspaces/Lab-ED1/zombcircle_apocalypse
   pkill -f pygbag; pkill -f http.server
   rm -f game/audio-pygbag.py
   rm -rf build
   python -m pygbag --build .
      python -m http.server 8080 --directory "$(pwd)/build/web"
```

1. Espera a que la terminal muestre que sirve en `http://localhost:8000`
   (en Codespaces, abre el puerto 8000 en la pestaña **Ports**).
2. Abre **http://localhost:8000** en el navegador. NO abras `index.html` con
   doble clic (`file://`): no funciona.
3. La primera carga tarda (descarga el runtime). Cuando aparezca el mensaje
   "Ready to start! Please click/touch page", haz clic en la página.
4. Si se queda cargando: pulsa F12, abre la pestaña **Console** y revisa el
   error; prueba Ctrl+Shift+R (recarga sin caché) o una ventana de incógnito.

Si `pygbag` no responde o falla al arrancar:

- Borra la carpeta `build/` y vuelve a ejecutar.
- Cierra cualquier proceso usando el puerto 8000 o usa
  `python -m pygbag --port 8001 .`.
- Usa un entorno virtual con Python 3.11 o 3.12 (las versiones muy nuevas
  de Python pueden no ser compatibles con pygbag).
- Verifica que `main.py` esté en la carpeta donde ejecutas el comando.

En el navegador el sistema de archivos es virtual: `logs/` y `config.json`
no persisten entre recargas.

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
