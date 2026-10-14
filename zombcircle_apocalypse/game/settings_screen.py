# ======================================================================
# ARCHIVO: game/settings_screen.py - ajustes del jugador (config.json)
# ======================================================================
# QUE ES: todo lo relacionado con los AJUSTES del juego.
# QUE HACE:
#   - Lee config.json (nombre, volumen, dificultad) y lo guarda de nuevo.
#   - Valida los datos: si alguien edita el archivo y pone basura, usa valores
#     por defecto en vez de romper el juego.
#   - Dibuja la pantalla SETTINGS y reacciona a las teclas.
# ======================================================================

"""Pantalla de configuracion y manejo de config.json (Persona 1).

json se usa SOLO aqui (config), nunca para la bitacora.

- load_config(): tolera archivo inexistente, vacio, con JSON invalido,
  con tipos incorrectos o con claves faltantes -> usa valores por defecto.
- save_config(): escribe a un archivo temporal y luego lo reemplaza, para
  que un cierre abrupto no deje config.json a medias.
"""
# json: unico uso permitido de json en el laboratorio (config.json).
import json
# os: para renombrar el archivo temporal al guardar.
import os
# sys: para saber si corremos en el navegador.
import sys

# pygame: para leer teclas y dibujar texto.
import pygame

# Lista de dificultades validas (easy, normal, hard).
from game.game_logic import DIFFICULTIES

# Valores por defecto si config.json falta o esta danado.
DEFAULT_CONFIG = {"player": "player", "volume": 80, "difficulty": "normal"}
# Maximo de letras del nombre del jugador.
MAX_NAME_LEN = 12
IS_WEB = sys.platform == "emscripten"   # navegador (pygbag)
# Aviso que se muestra en la web: los cambios se pierden al recargar.
WEB_NOTICE = "Web: los cambios no se guardan al recargar la pagina"
# Ademas de letras y numeros, el nombre puede llevar _ y -.
ALLOWED_EXTRA_CHARS = "_-"


# LIMPIAR LA CONFIG: recibe cualquier cosa y devuelve una config correcta.
# Cada campo se revisa por separado; si uno esta mal se reemplaza por su
# valor por defecto y los demas se conservan.
def sanitize_config(raw):
    """Devuelve una config valida a partir de CUALQUIER objeto.

    Cada campo se valida por separado: si uno es invalido se reemplaza
    por su valor por defecto y los demas se conservan.
    """
    # Partimos de una copia de los valores por defecto.
    config = dict(DEFAULT_CONFIG)
    # Si lo leido ni siquiera es un diccionario, devolvemos los defaults.
    if not isinstance(raw, dict):
        return config

    # NOMBRE: se quitan espacios, se dejan solo caracteres permitidos,
    # se recorta a 12 letras y solo se acepta si no queda vacio.
    name = raw.get("player")
    if isinstance(name, str):
        name = "".join(c for c in name.strip()
                       if c.isalnum() or c in ALLOWED_EXTRA_CHARS)
        name = name[:MAX_NAME_LEN]
        if name:
            config["player"] = name

    # VOLUMEN: debe ser numero (no True/False) y no NaN; se fuerza al rango 0-100.
    volume = raw.get("volume")
    if isinstance(volume, (int, float)) and not isinstance(volume, bool):
        if volume == volume:  # descarta NaN
            config["volume"] = int(min(100, max(0, volume)))

    # DIFICULTAD: debe ser texto y estar en la lista valida (sin importar mayusculas).
    difficulty = raw.get("difficulty")
    if isinstance(difficulty, str) and difficulty.lower() in DIFFICULTIES:
        config["difficulty"] = difficulty.lower()

    return config


# LEER config.json. Si el archivo no existe o esta roto, devuelve los defaults.
def load_config(path):
    """Carga config.json; ante cualquier problema devuelve los defaults."""
    # Intentamos abrir y leer el JSON.
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):  # ValueError cubre JSONDecodeError
        return dict(DEFAULT_CONFIG)
    return sanitize_config(raw)


# GUARDAR config.json. Primero se escribe en un archivo temporal y luego
# se reemplaza el original: asi, si algo falla a mitad, no se corrompe.
def save_config(path, config):
    """Guarda la config. Devuelve True si pudo escribir, False si no."""
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(sanitize_config(config), f, indent=2)
        os.replace(tmp_path, path)
        return True
    except OSError:
        return False


# PANTALLA DE AJUSTES: guarda cual campo esta seleccionado y los valores
# que se estan editando.
class SettingsScreen:
    """Pantalla SETTINGS: Player, Volume, Difficulty.

    Controles: arriba/abajo cambia de campo; izquierda/derecha ajusta
    volumen o dificultad; en Player se escribe y Backspace borra;
    Enter o Esc terminan (main.py guarda config.json al salir).
    """
    # Los tres campos editables, en orden.
    FIELDS = ("player", "volume", "difficulty")

    # Copia la config (ya validada) y empieza en el primer campo (Player).
    def __init__(self, config):
        self.config = sanitize_config(config)
        self.index = 0

    # Procesa una tecla. Devuelve True cuando el usuario quiere salir
    # (Enter o Esc); si no, False.
    def handle_event(self, event):
        """Procesa un evento. Devuelve True cuando el usuario sale."""
        if event.type != pygame.KEYDOWN:
            return False
        key = event.key
        if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
        # Flechas arriba/abajo cambian de campo (el '%' da la vuelta).
        if key == pygame.K_UP:
            self.index = (self.index - 1) % len(self.FIELDS)
        elif key == pygame.K_DOWN:
            self.index = (self.index + 1) % len(self.FIELDS)
        # Cualquier otra tecla se manda a editar el campo seleccionado.
        else:
            field = self.FIELDS[self.index]
            if field == "player":
                self._edit_name(event)
            elif field == "volume":
                self._edit_volume(key)
            else:
                self._edit_difficulty(key)
        return False

    # Editar nombre: Backspace borra la ultima letra; otras teclas agregan
    # el caracter si es valido y no se pasa del maximo.
    def _edit_name(self, event):
        name = self.config["player"]
        if event.key == pygame.K_BACKSPACE:
            self.config["player"] = name[:-1]
        elif (event.unicode and len(name) < MAX_NAME_LEN
              and (event.unicode.isalnum() or event.unicode in ALLOWED_EXTRA_CHARS)):
            self.config["player"] = name + event.unicode

    # Editar volumen: flecha derecha +5, izquierda -5, siempre entre 0 y 100.
    def _edit_volume(self, key):
        step = 5 if key == pygame.K_RIGHT else -5 if key == pygame.K_LEFT else 0
        self.config["volume"] = min(100, max(0, self.config["volume"] + step))

    # Editar dificultad: las flechas recorren easy -> normal -> hard
    # (y vuelven al inicio al pasarse).
    def _edit_difficulty(self, key):
        i = DIFFICULTIES.index(self.config["difficulty"])
        if key == pygame.K_RIGHT:
            i = (i + 1) % len(DIFFICULTIES)
        elif key == pygame.K_LEFT:
            i = (i - 1) % len(DIFFICULTIES)
        self.config["difficulty"] = DIFFICULTIES[i]

    # Dibuja la pantalla: titulo, las 3 filas (la elegida en amarillo),
    # una linea de ayuda abajo y, en la web, el aviso de que no se guarda.
    def draw(self, surface, font, big_font):
        """Dibuja la pantalla con primitivas de pygame."""
        surface.fill((20, 22, 30))
        title = big_font.render("SETTINGS", True, (240, 240, 240))
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 90)))

        # Texto de cada fila. El '_' al final del nombre simula el cursor.
        rows = (
            "Player:      " + self.config["player"]
            + ("_" if self.index == 0 else ""),
            "Volume:      < %d >" % self.config["volume"],
            "Difficulty:  < %s >" % self.config["difficulty"].capitalize(),
        )
        # Pintamos cada fila una debajo de otra.
        for i, text in enumerate(rows):
            selected = (i == self.index)
            color = (255, 210, 80) if selected else (200, 200, 200)
            img = font.render(text, True, color)
            surface.blit(img, (220, 200 + i * 60))
        # Linea de ayuda con los controles.
        hint = font.render("Up/Down: field   Left/Right: change   "
                           "Enter/Esc: save and back", True, (140, 140, 150))
        surface.blit(hint, hint.get_rect(center=(surface.get_width() // 2, 540)))
        # Solo en el navegador: mostrar el aviso.
        if IS_WEB:
            # En el navegador el disco es virtual: config.json se pierde al recargar.
            note = font.render(WEB_NOTICE, True, (230, 150, 80))
            surface.blit(note, note.get_rect(center=(surface.get_width() // 2, 480)))
