"""Logica pura de Zombcircle Apocalypse (Persona 1).

Este modulo NO importa pygame: solo calcula el estado del juego y emite
eventos mediante un callback ``emit(event_type, session_id, **params)``.
Asi la logica se puede probar sin ventana, y la escritura de la bitacora
(modulo ``telemetry``) queda desacoplada del juego.

Eventos que emite una partida (en este orden tipico):
    SESSION_START -> ENEMY_KILL / DAMAGE_TAKEN / LEVEL_UP ...
    -> PLAYER_DEATH (solo si muere) -> SESSION_END
"""
import math
import os
import random
import time

ARENA_W = 800
ARENA_H = 600

DIFFICULTIES = ("easy", "normal", "hard")

# Multiplicadores por dificultad (se aplican a los enemigos).
DIFFICULTY_PARAMS = {
    "easy": {"enemy_count": 0.8, "enemy_hp": 0.8,
             "enemy_damage": 0.7, "enemy_speed": 0.9},
    "normal": {"enemy_count": 1.0, "enemy_hp": 1.0,
               "enemy_damage": 1.0, "enemy_speed": 1.0},
    "hard": {"enemy_count": 1.3, "enemy_hp": 1.3,
             "enemy_damage": 1.4, "enemy_speed": 1.1},
}

# Tipos de enemigo. "weight" = probabilidad relativa de aparecer;
# "first_wave" = primera oleada en la que puede aparecer.
ENEMY_TYPES = {
    "slime": {"hp": 20, "speed": 60, "damage": 8, "points": 100,
              "radius": 14, "first_wave": 1, "weight": 5},
    "bat": {"hp": 10, "speed": 120, "damage": 5, "points": 150,
            "radius": 10, "first_wave": 2, "weight": 3},
    "brute": {"hp": 60, "speed": 45, "damage": 15, "points": 300,
              "radius": 20, "first_wave": 3, "weight": 2},
    "boss": {"hp": 300, "speed": 55, "damage": 25, "points": 1500,
             "radius": 34, "first_wave": 4, "weight": 0},
}
REGULAR_TYPES = ("slime", "bat", "brute")

PLAYER_MAX_HP = 100
PLAYER_SPEED = 230.0
PLAYER_RADIUS = 14
FIRE_COOLDOWN = 0.22
BULLET_SPEED = 520.0
BULLET_DAMAGE = 10
BULLET_RADIUS = 4
HEAL_ON_LEVEL_UP = 15
ATTACK_COOLDOWN = 0.8     # segundos entre golpes de un mismo enemigo
INTERMISSION = 1.5        # pausa entre oleadas
BOSS_EVERY = 4            # cada 4 oleadas aparece un jefe


class Enemy:
    """Enemigo con sus estadisticas ya ajustadas a la dificultad."""
    __slots__ = ("kind", "x", "y", "hp", "speed", "damage",
                 "radius", "points", "attack_cd")

    def __init__(self, kind, x, y, params):
        base = ENEMY_TYPES[kind]
        self.kind = kind
        self.x = x
        self.y = y
        self.hp = base["hp"] * params["enemy_hp"]
        self.speed = base["speed"] * params["enemy_speed"]
        self.damage = max(1, int(round(base["damage"] * params["enemy_damage"])))
        self.radius = base["radius"]
        self.points = base["points"]
        self.attack_cd = 0.0


class Bullet:
    """Proyectil del jugador."""
    __slots__ = ("x", "y", "vx", "vy")

    def __init__(self, x, y, vx, vy):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy


class SessionIdGenerator:
    """Genera session_id unicos con formato S0001, S0002, ...

    El ultimo numero usado se guarda en un archivo pequeno
    (``session_counter.txt``) FUERA de logs/, para no leer la bitacora
    solo para saber cual es el siguiente id.

    - Archivo inexistente  -> primera ejecucion, se empieza en S0001.
    - Archivo danado       -> se usa la hora actual como base, para no
                              repetir ids ya escritos en la bitacora.
    """

    def __init__(self, counter_path):
        self.counter_path = counter_path
        self._last = self._read()

    def _read(self):
        if not os.path.exists(self.counter_path):
            return 0
        try:
            with open(self.counter_path, "r", encoding="utf-8") as f:
                return int(f.readline().strip())
        except (OSError, ValueError):
            return int(time.time())

    def next_id(self):
        """Devuelve el siguiente id y lo persiste."""
        self._last += 1
        try:
            with open(self.counter_path, "w", encoding="utf-8") as f:
                f.write(str(self._last) + "\n")
        except OSError:
            pass  # si no se puede guardar, el contador sigue en memoria
        return "S%04d" % self._last


class ArenaGame:
    """Una partida (una sesion) de Zombcircle Apocalypse.

    emit: funcion ``emit(event_type, session_id, **params)``; en el juego
          real es ``TelemetryWriter.log``.
    """

    def __init__(self, player, difficulty, session_id, emit, rng=None):
        self.player_name = player
        self.difficulty = difficulty if difficulty in DIFFICULTY_PARAMS else "normal"
        self.params = DIFFICULTY_PARAMS[self.difficulty]
        self.session_id = session_id
        self._emit = emit
        self.rng = rng or random.Random()

        self.px = ARENA_W / 2
        self.py = ARENA_H / 2
        self.hp = PLAYER_MAX_HP
        self.score = 0
        self.level = 1            # oleada actual (= nivel)
        self.elapsed = 0.0        # tiempo de juego en segundos
        self.enemies = []
        self.bullets = []
        self.finished = False
        self.result = None        # "death" | "quit"

        self._fire_cd = 0.0
        self._spawn_queue = []
        self._spawn_timer = 0.0
        self._intermission = 0.0
        self._wave_active = False

    # ---------------------------------------------------------- eventos
    def _log(self, event_type, **params):
        self._emit(event_type, self.session_id, **params)

    def start(self):
        """Registra SESSION_START y arranca la oleada 1."""
        self._log("SESSION_START", player=self.player_name,
                  difficulty=self.difficulty)
        self._start_wave()

    def finish(self, result):
        """Cierra la sesion con SESSION_END (result: death | quit).

        Es idempotente: si ya termino, no vuelve a escribir nada.
        """
        if self.finished:
            return
        self.finished = True
        self.result = result
        self._log("SESSION_END", score=self.score, level=self.level,
                  duration=round(self.elapsed, 1), result=result)

    # ------------------------------------------------------ actualizacion
    def update(self, dt, move=(0, 0), aim=None):
        """Avanza la partida dt segundos.

        move: (dx, dy) con valores -1, 0 o 1.
        aim:  (x, y) del punto al que se dispara, o None si no dispara.
        """
        if self.finished:
            return
        self.elapsed += dt
        self._move_player(dt, move)
        self._handle_shooting(dt, aim)
        self._update_bullets(dt)
        self._update_waves(dt)
        self._update_enemies(dt)
        if self.finished:          # murio durante _update_enemies
            return
        self._resolve_bullet_hits()
        self._check_wave_cleared()

    def _move_player(self, dt, move):
        dx, dy = move
        length = math.hypot(dx, dy)
        if length > 0:
            self.px += dx / length * PLAYER_SPEED * dt
            self.py += dy / length * PLAYER_SPEED * dt
        self.px = min(max(self.px, PLAYER_RADIUS), ARENA_W - PLAYER_RADIUS)
        self.py = min(max(self.py, PLAYER_RADIUS), ARENA_H - PLAYER_RADIUS)

    def _handle_shooting(self, dt, aim):
        self._fire_cd = max(0.0, self._fire_cd - dt)
        if aim is None or self._fire_cd > 0:
            return
        ax = aim[0] - self.px
        ay = aim[1] - self.py
        dist = math.hypot(ax, ay)
        if dist < 1:
            return
        self.bullets.append(Bullet(self.px, self.py,
                                   ax / dist * BULLET_SPEED,
                                   ay / dist * BULLET_SPEED))
        self._fire_cd = FIRE_COOLDOWN

    def _update_bullets(self, dt):
        alive = []
        for b in self.bullets:
            b.x += b.vx * dt
            b.y += b.vy * dt
            if -10 <= b.x <= ARENA_W + 10 and -10 <= b.y <= ARENA_H + 10:
                alive.append(b)
        self.bullets = alive

    # ------------------------------------------------------------ oleadas
    def _start_wave(self):
        """Prepara la cola de enemigos de la oleada actual."""
        count = max(1, int(round((3 + 2 * self.level)
                                 * self.params["enemy_count"])))
        pool = [k for k in REGULAR_TYPES
                if ENEMY_TYPES[k]["first_wave"] <= self.level]
        weights = [ENEMY_TYPES[k]["weight"] for k in pool]
        queue = self.rng.choices(pool, weights=weights, k=count)
        if self.level % BOSS_EVERY == 0:
            queue.append("boss")
        self._spawn_queue = queue
        self._spawn_timer = 0.5
        self._wave_active = True

    def _spawn_interval(self):
        return max(0.25, 0.8 - 0.03 * self.level)

    def _spawn_enemy(self, kind):
        side = self.rng.randint(0, 3)
        if side == 0:
            x, y = self.rng.uniform(0, ARENA_W), -20
        elif side == 1:
            x, y = self.rng.uniform(0, ARENA_W), ARENA_H + 20
        elif side == 2:
            x, y = -20, self.rng.uniform(0, ARENA_H)
        else:
            x, y = ARENA_W + 20, self.rng.uniform(0, ARENA_H)
        self.enemies.append(Enemy(kind, x, y, self.params))

    def _update_waves(self, dt):
        if self._intermission > 0:
            self._intermission -= dt
            if self._intermission <= 0:
                self._start_wave()
            return
        if self._spawn_queue:
            self._spawn_timer -= dt
            if self._spawn_timer <= 0:
                self._spawn_enemy(self._spawn_queue.pop(0))
                self._spawn_timer = self._spawn_interval()

    def _check_wave_cleared(self):
        """Si la oleada termino, sube de nivel y registra LEVEL_UP."""
        if self._wave_active and not self._spawn_queue and not self.enemies:
            self._wave_active = False
            self.level += 1
            self.score += 50 * self.level
            self.hp = min(PLAYER_MAX_HP, self.hp + HEAL_ON_LEVEL_UP)
            self._log("LEVEL_UP", level=self.level,
                      time=round(self.elapsed, 1))
            self._intermission = INTERMISSION

    # ---------------------------------------------------------- combate
    def _update_enemies(self, dt):
        for e in self.enemies:
            dx = self.px - e.x
            dy = self.py - e.y
            dist = math.hypot(dx, dy)
            if dist > 0:
                e.x += dx / dist * e.speed * dt
                e.y += dy / dist * e.speed * dt
            e.attack_cd = max(0.0, e.attack_cd - dt)
            if dist <= e.radius + PLAYER_RADIUS and e.attack_cd <= 0:
                self._hit_player(e)
                if self.finished:
                    return

    def _hit_player(self, enemy):
        self.hp = max(0, self.hp - enemy.damage)
        enemy.attack_cd = ATTACK_COOLDOWN
        self._log("DAMAGE_TAKEN", amount=enemy.damage, source=enemy.kind)
        if self.hp <= 0:
            self._log("PLAYER_DEATH", cause=enemy.kind, level=self.level)
            self.finish("death")

    def _resolve_bullet_hits(self):
        alive_bullets = []
        for b in self.bullets:
            hit = False
            for e in self.enemies:
                if e.hp <= 0:
                    continue
                if math.hypot(b.x - e.x, b.y - e.y) <= e.radius + BULLET_RADIUS:
                    e.hp -= BULLET_DAMAGE
                    hit = True
                    if e.hp <= 0:
                        self._kill(e)
                    break
            if not hit:
                alive_bullets.append(b)
        self.bullets = alive_bullets
        self.enemies = [e for e in self.enemies if e.hp > 0]

    def _kill(self, enemy):
        self.score += enemy.points
        self._log("ENEMY_KILL", type=enemy.kind, wave=self.level)
