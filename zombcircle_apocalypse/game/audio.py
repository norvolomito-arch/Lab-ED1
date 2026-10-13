"""Musica de fondo de Zombcircle Apocalypse (local y navegador).

Coloca el archivo de musica en ``assets/music/`` con el nombre ``theme.ogg``.
En ejecucion local tambien se aceptan ``theme.wav`` y ``theme.mp3``; en el
navegador (pygbag, sys.platform == "emscripten") solo se usa ``theme.ogg``.
Si hay varios, se usa el primero que cargue bien. Si no existe ninguno, o el
equipo no tiene dispositivo de audio (por ejemplo un Codespace),
``MusicPlayer`` no hace nada y el juego sigue normal.

Un solo modulo sirve para ambos entornos: no hace falta una copia aparte
para pygbag.
"""
import os
import sys

import pygame

# True cuando el juego corre dentro del navegador (pygbag / emscripten).
IS_WEB = sys.platform == "emscripten"

# Nombres aceptados, en orden de preferencia.
MUSIC_FILENAMES_LOCAL = ("theme.ogg", "theme.wav", "theme.mp3")
MUSIC_FILENAMES_WEB = ("theme.ogg",)
MUSIC_FILENAMES = MUSIC_FILENAMES_WEB if IS_WEB else MUSIC_FILENAMES_LOCAL


def find_music_files(music_dir):
    """Devuelve las rutas de musica existentes, en orden de preferencia."""
    paths = []
    for name in MUSIC_FILENAMES:
        path = os.path.join(music_dir, name)
        if os.path.isfile(path):
            paths.append(path)
    return paths


class MusicPlayer:
    """Reproduce musica en bucle; nunca lanza excepciones por falta de audio."""

    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.playing = False

    def start(self, volume):
        """Inicia la musica con volumen 0-100. Sin archivo o sin audio: no-op.

        Prueba los archivos en orden; si uno no se puede cargar (por ejemplo
        un .ogg con codec Opus, que pygame no lee), avisa y prueba el
        siguiente. Los avisos salen por consola para poder diagnosticar.
        """
        paths = find_music_files(self.music_dir)
        if not paths:
            return
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as error:
            print("AVISO: sin dispositivo de audio (%s); se juega sin musica."
                  % error)
            return
        for path in paths:
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.set_volume(self._to_unit(volume))
                pygame.mixer.music.play(-1)       # -1 = bucle infinito
                self.playing = True
                print("Musica: %s (volumen %d)" % (os.path.basename(path), volume))
                return
            except (pygame.error, OSError) as error:
                print("AVISO: no se pudo cargar %s (%s)"
                      % (os.path.basename(path), error))

    def set_volume(self, volume):
        """Aplica un nuevo volumen 0-100 si hay musica sonando."""
        if not self.playing:
            return
        try:
            pygame.mixer.music.set_volume(self._to_unit(volume))
        except pygame.error:
            pass

    def stop(self):
        """Detiene la musica (se llama al cerrar el juego)."""
        if not self.playing:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        self.playing = False

    @staticmethod
    def _to_unit(volume):
        """Convierte el volumen de config.json (0-100) a 0.0-1.0."""
        return min(1.0, max(0.0, volume / 100.0))
