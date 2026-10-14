# ======================================================================
# ARCHIVO: game/audio.py - la musica de fondo
# ======================================================================
# QUE ES: reproduce la musica del juego en bucle.
# DETALLE IMPORTANTE: si no hay archivo de musica o la computadora no tiene
# audio, el juego sigue funcionando sin sonido (nunca se cae por esto).
# La musica esperada esta en assets/music/theme.ogg.
# ======================================================================

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
# sys: para saber si estamos en el navegador.
import sys

# pygame trae el modulo 'mixer', que reproduce sonido.
import pygame

# True cuando el juego corre dentro del navegador (pygbag / emscripten).
# True cuando corre en el navegador (pygbag).
IS_WEB = sys.platform == "emscripten"

# Nombres aceptados, en orden de preferencia.
# Nombres de archivo que se buscan, en orden de preferencia.
# En el navegador solo sirve .ogg.
MUSIC_FILENAMES_LOCAL = ("theme.ogg", "theme.wav", "theme.mp3")
MUSIC_FILENAMES_WEB = ("theme.ogg",)
MUSIC_FILENAMES = MUSIC_FILENAMES_WEB if IS_WEB else MUSIC_FILENAMES_LOCAL


# Revisa la carpeta de musica y devuelve las rutas de los archivos que SI existen.
def find_music_files(music_dir):
    """Devuelve las rutas de musica existentes, en orden de preferencia."""
    paths = []
    for name in MUSIC_FILENAMES:
        path = os.path.join(music_dir, name)
        if os.path.isfile(path):
            paths.append(path)
    return paths


# REPRODUCTOR: arrancar, cambiar volumen y detener la musica.
class MusicPlayer:
    """Reproduce musica en bucle; nunca lanza excepciones por falta de audio."""

    # Guarda la carpeta de musica y marca que todavia no suena nada.
    def __init__(self, music_dir):
        self.music_dir = music_dir
        self.playing = False

    # Inicia la musica con volumen 0-100. Si no hay archivo o no hay audio,
    # no hace nada. Prueba cada archivo hasta que uno funcione.
    def start(self, volume):
        """Inicia la musica con volumen 0-100. Sin archivo o sin audio: no-op.

        Prueba los archivos en orden; si uno no se puede cargar (por ejemplo
        un .ogg con codec Opus, que pygame no lee), avisa y prueba el
        siguiente. Los avisos salen por consola para poder diagnosticar.
        """
        # Buscamos que archivos hay; si no hay ninguno, salimos.
        paths = find_music_files(self.music_dir)
        if not paths:
            return
        # Preparamos el dispositivo de audio; si falla, avisamos y seguimos sin musica.
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error as error:
            print("AVISO: sin dispositivo de audio (%s); se juega sin musica."
                  % error)
            return
        # Intentamos cargar cada archivo; con el primero que funcione, lo ponemos
        # en bucle infinito (-1) y terminamos.
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

    # Cambia el volumen mientras suena la musica.
    def set_volume(self, volume):
        """Aplica un nuevo volumen 0-100 si hay musica sonando."""
        if not self.playing:
            return
        try:
            pygame.mixer.music.set_volume(self._to_unit(volume))
        except pygame.error:
            pass

    # Detiene la musica (al cerrar el juego).
    def stop(self):
        """Detiene la musica (se llama al cerrar el juego)."""
        if not self.playing:
            return
        try:
            pygame.mixer.music.stop()
        except pygame.error:
            pass
        self.playing = False

    # Funcion auxiliar que no necesita el objeto.
    @staticmethod
    # Convierte el volumen de 0-100 (como en config.json) a 0.0-1.0
    # (lo que pide pygame).
    def _to_unit(volume):
        """Convierte el volumen de config.json (0-100) a 0.0-1.0."""
        return min(1.0, max(0.0, volume / 100.0))
