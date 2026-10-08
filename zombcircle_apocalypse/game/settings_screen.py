"""Pantalla de configuracion y manejo de config.json (Persona 1).

json se usa SOLO aqui (config), nunca para la bitacora.

- load_config(): tolera archivo inexistente, vacio, con JSON invalido,
  con tipos incorrectos o con claves faltantes -> usa valores por defecto.
- save_config(): escribe a un archivo temporal y luego lo reemplaza, para
  que un cierre abrupto no deje config.json a medias.
"""
import json
import os

import pygame

from game.game_logic import DIFFICULTIES

DEFAULT_CONFIG = {"player": "player", "volume": 80, "difficulty": "normal"}
MAX_NAME_LEN = 12
ALLOWED_EXTRA_CHARS = "_-"


def sanitize_config(raw):
    """Devuelve una config valida a partir de CUALQUIER objeto.

    Cada campo se valida por separado: si uno es invalido se reemplaza
    por su valor por defecto y los demas se conservan.
    """
    config = dict(DEFAULT_CONFIG)
    if not isinstance(raw, dict):
        return config

    name = raw.get("player")
    if isinstance(name, str):
        name = "".join(c for c in name.strip()
                       if c.isalnum() or c in ALLOWED_EXTRA_CHARS)
        name = name[:MAX_NAME_LEN]
        if name:
            config["player"] = name

    volume = raw.get("volume")
    if isinstance(volume, (int, float)) and not isinstance(volume, bool):
        if volume == volume:  # descarta NaN
            config["volume"] = int(min(100, max(0, volume)))

    difficulty = raw.get("difficulty")
    if isinstance(difficulty, str) and difficulty.lower() in DIFFICULTIES:
        config["difficulty"] = difficulty.lower()

    return config


def load_config(path):
    """Carga config.json; ante cualquier problema devuelve los defaults."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            raw = json.load(f)
    except (OSError, ValueError):  # ValueError cubre JSONDecodeError
        return dict(DEFAULT_CONFIG)
    return sanitize_config(raw)


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


class SettingsScreen:
    """Pantalla SETTINGS: Player, Volume, Difficulty.

    Controles: arriba/abajo cambia de campo; izquierda/derecha ajusta
    volumen o dificultad; en Player se escribe y Backspace borra;
    Enter o Esc terminan (main.py guarda config.json al salir).
    """
    FIELDS = ("player", "volume", "difficulty")

    def __init__(self, config):
        self.config = sanitize_config(config)
        self.index = 0

    def handle_event(self, event):
        """Procesa un evento. Devuelve True cuando el usuario sale."""
        if event.type != pygame.KEYDOWN:
            return False
        key = event.key
        if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_KP_ENTER):
            return True
        if key == pygame.K_UP:
            self.index = (self.index - 1) % len(self.FIELDS)
        elif key == pygame.K_DOWN:
            self.index = (self.index + 1) % len(self.FIELDS)
        else:
            field = self.FIELDS[self.index]
            if field == "player":
                self._edit_name(event)
            elif field == "volume":
                self._edit_volume(key)
            else:
                self._edit_difficulty(key)
        return False

    def _edit_name(self, event):
        name = self.config["player"]
        if event.key == pygame.K_BACKSPACE:
            self.config["player"] = name[:-1]
        elif (event.unicode and len(name) < MAX_NAME_LEN
              and (event.unicode.isalnum() or event.unicode in ALLOWED_EXTRA_CHARS)):
            self.config["player"] = name + event.unicode

    def _edit_volume(self, key):
        step = 5 if key == pygame.K_RIGHT else -5 if key == pygame.K_LEFT else 0
        self.config["volume"] = min(100, max(0, self.config["volume"] + step))

    def _edit_difficulty(self, key):
        i = DIFFICULTIES.index(self.config["difficulty"])
        if key == pygame.K_RIGHT:
            i = (i + 1) % len(DIFFICULTIES)
        elif key == pygame.K_LEFT:
            i = (i - 1) % len(DIFFICULTIES)
        self.config["difficulty"] = DIFFICULTIES[i]

    def draw(self, surface, font, big_font):
        """Dibuja la pantalla con primitivas de pygame."""
        surface.fill((20, 22, 30))
        title = big_font.render("SETTINGS", True, (240, 240, 240))
        surface.blit(title, title.get_rect(center=(surface.get_width() // 2, 90)))

        rows = (
            "Player:      " + self.config["player"]
            + ("_" if self.index == 0 else ""),
            "Volume:      < %d >" % self.config["volume"],
            "Difficulty:  < %s >" % self.config["difficulty"].capitalize(),
        )
        for i, text in enumerate(rows):
            selected = (i == self.index)
            color = (255, 210, 80) if selected else (200, 200, 200)
            img = font.render(text, True, color)
            surface.blit(img, (220, 200 + i * 60))
        hint = font.render("Up/Down: field   Left/Right: change   "
                           "Enter/Esc: save and back", True, (140, 140, 150))
        surface.blit(hint, hint.get_rect(center=(surface.get_width() // 2, 540)))
