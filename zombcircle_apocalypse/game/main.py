"""Punto de entrada de Zombcircle Apocalypse (Persona 1).

Bucle principal compatible con pygbag: async/await, ``await
asyncio.sleep(0)`` en cada fotograma, sin hilos ni dependencias nativas.

Ejecutar desde la raiz del repo:   python -m game.main
"""
import asyncio
import os
import sys

import pygame

# La raiz del repo debe estar en sys.path para importar ``telemetry``.
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.insert(0, BASE_DIR)

from telemetry import TelemetryWriter                     # noqa: E402
from game.audio import MusicPlayer                        # noqa: E402
from game.game_logic import (ArenaGame, SessionIdGenerator,  # noqa: E402
                             ARENA_W, ARENA_H)
from game.settings_screen import (SettingsScreen, load_config,  # noqa: E402
                                  sanitize_config, save_config)

CONFIG_PATH = os.path.join(BASE_DIR, "config.json")
LOG_DIR = os.path.join(BASE_DIR, "logs")
COUNTER_PATH = os.path.join(BASE_DIR, "session_counter.txt")
ICON_PATH = os.path.join(BASE_DIR, "assets", "icon.png")
MUSIC_DIR = os.path.join(BASE_DIR, "assets", "music")

GAME_TITLE = "Zombcircle Apocalypse"

BUFFER_SIZE = 25            # PROVISIONAL: se justifica con el Experimento A
MAX_LOG_BYTES = 512 * 1024  # umbral de rotacion (512 KB)
FPS = 60

MENU_ITEMS = ("Start Game", "Statistics", "Settings", "Quit")
ENEMY_COLORS = {"slime": (80, 200, 90), "bat": (170, 110, 220),
                "brute": (230, 140, 50), "boss": (220, 50, 50)}


def open_statistics():
    """STUB de Statistics. La Persona 3 reemplaza esta funcion.

    Por ahora no hace nada: el menu solo la invoca.
    """
    pass


class App:
    """Maquina de estados: menu -> playing -> gameover, y settings."""

    def __init__(self, screen, writer, ids, config, music=None):
        self.screen = screen
        self.music = music
        self.writer = writer
        self.ids = ids
        self.config = config
        self.font = pygame.font.Font(None, 32)
        self.big_font = pygame.font.Font(None, 72)
        self.state = "menu"
        self.menu_index = 0
        self.menu_rects = []
        self.game = None
        self.settings = None
        self.running = True

    # ------------------------------------------------------- acciones
    def start_game(self):
        session_id = self.ids.next_id()
        self.game = ArenaGame(self.config["player"], self.config["difficulty"],
                              session_id, self.writer.log)
        self.game.start()
        self.state = "playing"

    def activate_menu(self, index):
        item = MENU_ITEMS[index]
        if item == "Start Game":
            self.start_game()
        elif item == "Statistics":
            open_statistics()
        elif item == "Settings":
            self.settings = SettingsScreen(self.config)
            self.state = "settings"
        elif item == "Quit":
            self.running = False

    def shutdown(self):
        """Cierra la partida activa (si la hay) para no dejar sesiones
        incompletas por una salida normal (Quit o cierre de ventana)."""
        if self.game is not None and not self.game.finished:
            self.game.finish("quit")

    # -------------------------------------------------------- eventos
    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.running = False
        elif self.state == "menu":
            self._menu_event(event)
        elif self.state == "settings":
            if self.settings.handle_event(event):
                self.config = sanitize_config(self.settings.config)
                save_config(CONFIG_PATH, self.config)
                if self.music is not None:
                    self.music.set_volume(self.config["volume"])
                self.state = "menu"
        elif self.state == "playing":
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.game.finish("quit")
                self.state = "gameover"
        elif self.state == "gameover":
            if event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                self.state = "menu"

    def _menu_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP:
                self.menu_index = (self.menu_index - 1) % len(MENU_ITEMS)
            elif event.key == pygame.K_DOWN:
                self.menu_index = (self.menu_index + 1) % len(MENU_ITEMS)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                self.activate_menu(self.menu_index)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            for i, rect in enumerate(self.menu_rects):
                if rect.collidepoint(event.pos):
                    self.menu_index = i
                    self.activate_menu(i)
                    break

    # ----------------------------------------------------- actualizar
    def update(self, dt):
        if self.state != "playing":
            return
        keys = pygame.key.get_pressed()
        dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
        dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
        aim = pygame.mouse.get_pos() if pygame.mouse.get_pressed()[0] else None
        self.game.update(dt, (dx, dy), aim)
        if self.game.finished:
            self.state = "gameover"

    # ---------------------------------------------------------- dibujo
    def _text(self, text, font, color, center):
        img = font.render(text, True, color)
        self.screen.blit(img, img.get_rect(center=center))

    def draw(self):
        if self.state == "menu":
            self._draw_menu()
        elif self.state == "settings":
            self.settings.draw(self.screen, self.font, self.big_font)
        elif self.state == "playing":
            self._draw_game()
        elif self.state == "gameover":
            self._draw_game()
            self._draw_gameover()

    def _draw_menu(self):
        self.screen.fill((20, 22, 30))
        self._text(GAME_TITLE.upper(), self.big_font, (240, 240, 240),
                   (ARENA_W // 2, 120))
        self.menu_rects = []
        for i, item in enumerate(MENU_ITEMS):
            color = (255, 210, 80) if i == self.menu_index else (200, 200, 200)
            center = (ARENA_W // 2, 250 + i * 70)
            self._text(item, self.font, color, center)
            self.menu_rects.append(pygame.Rect(center[0] - 120, center[1] - 25, 240, 50))
        self._text("WASD / arrows: move   Mouse: shoot   Esc: leave match",
                   self.font, (140, 140, 150), (ARENA_W // 2, 560))

    def _draw_game(self):
        g = self.game
        self.screen.fill((28, 32, 40))
        pygame.draw.rect(self.screen, (70, 76, 90), (0, 0, ARENA_W, ARENA_H), 3)
        for b in g.bullets:
            pygame.draw.circle(self.screen, (255, 240, 120), (int(b.x), int(b.y)), 4)
        for e in g.enemies:
            pygame.draw.circle(self.screen, ENEMY_COLORS[e.kind],
                               (int(e.x), int(e.y)), e.radius)
        pygame.draw.circle(self.screen, (90, 170, 255), (int(g.px), int(g.py)), 14)
        # HUD: vida como barra y datos de la partida como texto
        pygame.draw.rect(self.screen, (80, 30, 30), (15, 15, 200, 16))
        pygame.draw.rect(self.screen, (220, 60, 60), (15, 15, 2 * g.hp, 16))
        info = "%s | Wave %d | Score %d | %s" % (
            g.player_name, g.level, g.score, g.difficulty)
        self.screen.blit(self.font.render(info, True, (230, 230, 230)), (15, 40))

    def _draw_gameover(self):
        g = self.game
        veil = pygame.Surface((ARENA_W, ARENA_H))
        veil.set_alpha(150)
        self.screen.blit(veil, (0, 0))
        title = "YOU DIED" if g.result == "death" else "MATCH ENDED"
        self._text(title, self.big_font, (240, 240, 240), (ARENA_W // 2, 200))
        summary = "Score %d   Level %d   Time %.1fs" % (g.score, g.level, g.elapsed)
        self._text(summary, self.font, (230, 230, 230), (ARENA_W // 2, 290))
        self._text("Press any key to go back to the menu", self.font,
                   (170, 170, 180), (ARENA_W // 2, 350))


class _NullWriter:
    """Escritor vacio: se usa si no se puede crear la carpeta de bitacoras.

    Asi el juego sigue funcionando (por ejemplo en un navegador con sistema
    de archivos de solo lectura) en vez de quedarse en pantalla negra.
    """

    def log(self, event_type, session_id, **params):
        pass

    def flush(self):
        pass

    def close(self):
        pass


def open_writer():
    """Crea el TelemetryWriter; ante un error de disco devuelve _NullWriter."""
    try:
        return TelemetryWriter(LOG_DIR, BUFFER_SIZE, MAX_LOG_BYTES)
    except OSError as error:
        print("AVISO: no se pudo abrir la bitacora (%s); se juega sin ella."
              % error)
        return _NullWriter()


def load_icon():
    """Carga el icono de la ventana; si falta el archivo, no pasa nada."""
    try:
        return pygame.image.load(ICON_PATH)
    except (pygame.error, OSError):
        return None


async def main():
    pygame.init()
    icon = load_icon()
    if icon is not None:
        pygame.display.set_icon(icon)   # antes de set_mode, como recomienda pygame
    screen = pygame.display.set_mode((ARENA_W, ARENA_H))
    pygame.display.set_caption(GAME_TITLE)
    clock = pygame.time.Clock()

    config = load_config(CONFIG_PATH)
    ids = SessionIdGenerator(COUNTER_PATH)
    writer = open_writer()
    music = MusicPlayer(MUSIC_DIR)
    music.start(config["volume"])      # sin assets/music/theme.ogg no hace nada
    app = App(screen, writer, ids, config, music)
    try:
        while app.running:
            dt = min(clock.tick(FPS) / 1000.0, 0.05)  # tope por si hay lag
            for event in pygame.event.get():
                app.handle_event(event)
            app.update(dt)
            app.draw()
            pygame.display.flip()
            await asyncio.sleep(0)   # cede el control (requisito de pygbag)
    finally:
        # Cierre seguro: termina la sesion activa y vacia el buffer a disco.
        try:
            app.shutdown()
        finally:
            writer.close()
            music.stop()
            pygame.quit()


if __name__ == "__main__":
    asyncio.run(main())
