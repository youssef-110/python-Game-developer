"""Lumen: you are a lantern in the dark.

Your light burns down over time. Collect motes of light to keep it alive while shadows
hunt you. A shadow that touches you drains your light; a dash (Space) lets you slip
past them. The run ends when your light goes out.

Controls: WASD or arrow keys to move, Space to dash, Esc to quit, Enter to restart.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field

import pygame

WIDTH, HEIGHT = 960, 640
FPS = 60

# Light is both your health and how far you can see.
LIGHT_MAX = 100.0
LIGHT_START = 70.0
LIGHT_BURN = 2.2  # per second
MOTE_LIGHT = 9.0
SHADOW_DRAIN = 18.0
HIT_COOLDOWN = 0.8  # seconds of safety after a hit

PLAYER_SPEED = 240.0
DASH_SPEED = 720.0
DASH_TIME = 0.16
DASH_COOLDOWN = 0.9
PLAYER_RADIUS = 12


def vision_radius(light: float) -> float:
    return 70 + light * 2.6


@dataclass
class Shadow:
    x: float
    y: float
    speed: float
    radius: float = 15
    wobble: float = field(default_factory=lambda: random.uniform(0, math.tau))


@dataclass
class Mote:
    x: float
    y: float
    age: float = 0.0


class World:
    """Game state and rules. No drawing here, so it runs headless in tests."""

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)
        self.reset()

    def reset(self) -> None:
        self.px, self.py = WIDTH / 2, HEIGHT / 2
        self.light = LIGHT_START
        self.score = 0
        self.time = 0.0
        self.wave = 1
        self.shadows: list[Shadow] = []
        self.motes: list[Mote] = []
        self.dash_left = 0.0
        self.dash_ready = 0.0
        self.dash_dir = (0.0, 0.0)
        self.invulnerable = 0.0
        self.over = False
        for _ in range(4):
            self.spawn_mote()
        self.spawn_wave()

    # --- spawning ---------------------------------------------------------

    def spawn_mote(self) -> None:
        for _ in range(20):  # keep motes away from the player so they must be fetched
            x, y = self.rng.uniform(40, WIDTH - 40), self.rng.uniform(40, HEIGHT - 40)
            if math.dist((x, y), (self.px, self.py)) > 120:
                break
        self.motes.append(Mote(x, y))

    def spawn_shadow(self) -> None:
        side = self.rng.randrange(4)
        x = self.rng.uniform(0, WIDTH) if side < 2 else (-30 if side == 2 else WIDTH + 30)
        y = (-30 if side == 0 else HEIGHT + 30) if side < 2 else self.rng.uniform(0, HEIGHT)
        speed = 70 + self.wave * 9 + self.rng.uniform(-10, 15)
        self.shadows.append(Shadow(x, y, min(speed, 200)))

    def spawn_wave(self) -> None:
        for _ in range(2 + self.wave):
            self.spawn_shadow()

    # --- update -----------------------------------------------------------

    def dash(self, dx: float, dy: float) -> bool:
        if self.dash_ready > 0 or (dx == 0 and dy == 0):
            return False
        n = math.hypot(dx, dy)
        self.dash_dir = (dx / n, dy / n)
        self.dash_left = DASH_TIME
        self.dash_ready = DASH_COOLDOWN
        return True

    def update(self, dt: float, dx: float = 0.0, dy: float = 0.0) -> None:
        if self.over:
            return
        self.time += dt
        self.dash_ready = max(0.0, self.dash_ready - dt)
        self.invulnerable = max(0.0, self.invulnerable - dt)

        # Movement: a dash overrides steering for a moment.
        if self.dash_left > 0:
            self.dash_left -= dt
            vx, vy = self.dash_dir[0] * DASH_SPEED, self.dash_dir[1] * DASH_SPEED
        else:
            n = math.hypot(dx, dy)
            vx, vy = (dx / n * PLAYER_SPEED, dy / n * PLAYER_SPEED) if n else (0.0, 0.0)
        self.px = min(max(self.px + vx * dt, PLAYER_RADIUS), WIDTH - PLAYER_RADIUS)
        self.py = min(max(self.py + vy * dt, PLAYER_RADIUS), HEIGHT - PLAYER_RADIUS)

        # Light burns faster the longer you survive.
        self.light -= LIGHT_BURN * (1 + self.time / 120) * dt

        for mote in self.motes[:]:
            mote.age += dt
            if math.dist((mote.x, mote.y), (self.px, self.py)) < PLAYER_RADIUS + 10:
                self.motes.remove(mote)
                self.light = min(LIGHT_MAX, self.light + MOTE_LIGHT)
                self.score += 10
                self.spawn_mote()

        dashing = self.dash_left > 0
        for s in self.shadows:
            ang = math.atan2(self.py - s.y, self.px - s.x)
            s.wobble += dt * 3
            # A slight sideways wobble makes shadows curve in instead of beelining.
            ang += math.sin(s.wobble) * 0.35
            s.x += math.cos(ang) * s.speed * dt
            s.y += math.sin(ang) * s.speed * dt
            touching = math.dist((s.x, s.y), (self.px, self.py)) < s.radius + PLAYER_RADIUS
            if touching and not dashing and self.invulnerable <= 0:
                self.light -= SHADOW_DRAIN
                self.invulnerable = HIT_COOLDOWN
                # Knock the shadow back so one hit is one hit.
                s.x -= math.cos(ang) * 90
                s.y -= math.sin(ang) * 90

        # A new wave every 20 seconds.
        if self.time >= self.wave * 20:
            self.wave += 1
            self.spawn_wave()

        if self.light <= 0:
            self.light = 0
            self.over = True


# --- drawing ---------------------------------------------------------------

BG = (8, 9, 16)
FLOOR = (26, 24, 34)
WARM = (255, 196, 110)
MOTE = (255, 236, 170)
SHADOW = (4, 4, 8)
TEXT = (236, 228, 214)


def make_floor() -> pygame.Surface:
    """A stone floor pattern, drawn once."""
    floor = pygame.Surface((WIDTH, HEIGHT))
    floor.fill(FLOOR)
    rng = random.Random(3)
    for y in range(0, HEIGHT, 40):
        offset = 0 if (y // 40) % 2 == 0 else 30
        for x in range(-offset, WIDTH, 60):
            shade = rng.randint(-6, 6)
            color = tuple(max(0, c + shade) for c in FLOOR)
            pygame.draw.rect(floor, color, (x + 2, y + 2, 56, 36), border_radius=4)
    return floor


class Renderer:
    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.floor = make_floor()
        self.font = pygame.font.SysFont("georgia", 22)
        self.big = pygame.font.SysFont("georgia", 56)
        self.glow_cache: dict[int, pygame.Surface] = {}

    def glow(self, radius: int, color: tuple[int, int, int]) -> pygame.Surface:
        key = radius * 1000 + color[0]
        if key not in self.glow_cache:
            surf = pygame.Surface((radius * 2, radius * 2), pygame.SRCALPHA)
            for i in range(radius, 0, -2):
                a = int(90 * (1 - i / radius) ** 1.5)
                pygame.draw.circle(surf, (*color, a), (radius, radius), i)
            self.glow_cache[key] = surf
        return self.glow_cache[key]

    def warm_light(self, radius: int) -> pygame.Surface:
        """Black surface with a warm falloff, for additive blending (which ignores alpha)."""
        key = -radius
        if key not in self.glow_cache:
            surf = pygame.Surface((radius * 2, radius * 2))
            for i in range(radius, 0, -3):
                k = 0.28 * (1 - i / radius) ** 1.8
                pygame.draw.circle(surf, tuple(int(c * k) for c in WARM), (radius, radius), i)
            self.glow_cache[key] = surf
        return self.glow_cache[key]

    def darkness(self, world: World) -> pygame.Surface:
        # Full-screen darkness with a radial hole at the player.
        dark = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        dark.fill((*BG, 255))
        flicker = 1 + math.sin(world.time * 11) * 0.015 + math.sin(world.time * 3.7) * 0.02
        r = int(vision_radius(world.light) * flicker)
        hole = pygame.Surface((r * 2, r * 2), pygame.SRCALPHA)
        hole.fill((*BG, 255))  # the square's corners stay fully dark
        for i in range(r, 0, -4):
            alpha = int(255 * (i / r) ** 2.4)
            pygame.draw.circle(hole, (*BG, alpha), (r, r), i)
        dark.fill((0, 0, 0, 0), (world.px - r, world.py - r, r * 2, r * 2))
        dark.blit(hole, (world.px - r, world.py - r))
        return dark

    def draw(self, world: World) -> None:
        s = self.screen
        s.blit(self.floor, (0, 0))

        for sh in world.shadows:
            pulse = 1 + math.sin(sh.wobble * 2) * 0.08
            pygame.draw.circle(s, SHADOW, (int(sh.x), int(sh.y)), int(sh.radius * pulse))
            for k in (-1, 1):  # two faint eyes
                pygame.draw.circle(s, (120, 40, 60), (int(sh.x + k * 5), int(sh.y - 3)), 2)

        s.blit(self.darkness(world), (0, 0))

        # Motes are light, so they glow through the dark; shadows stay hidden in it.
        for m in world.motes:
            bob = math.sin(m.age * 3) * 3
            s.blit(self.glow(26, MOTE), (m.x - 26, m.y - 26 + bob))
            pygame.draw.circle(s, MOTE, (int(m.x), int(m.y + bob)), 4)

        # Warm cast of the lantern light. Radius is rounded so the glow cache stays small.
        warm = max(32, int(vision_radius(world.light) * 0.75) // 16 * 16)
        s.blit(self.warm_light(warm), (world.px - warm, world.py - warm), special_flags=pygame.BLEND_RGB_ADD)

        # The lantern sits above the darkness.
        s.blit(self.glow(48, WARM), (world.px - 48, world.py - 48))
        blink = world.invulnerable > 0 and int(world.time * 20) % 2 == 0
        if not blink:
            pygame.draw.circle(s, WARM, (int(world.px), int(world.py)), PLAYER_RADIUS)
            pygame.draw.circle(s, (255, 244, 220), (int(world.px), int(world.py)), 5)

        self.hud(world)

    def hud(self, world: World) -> None:
        s = self.screen
        pygame.draw.rect(s, (40, 36, 46), (24, 22, 204, 12), border_radius=6)
        pygame.draw.rect(s, WARM, (26, 24, int(200 * world.light / LIGHT_MAX), 8), border_radius=4)
        s.blit(self.font.render(f"{world.score}", True, TEXT), (24, 42))
        wave = self.font.render(f"Wave {world.wave}", True, TEXT)
        s.blit(wave, (WIDTH - wave.get_width() - 24, 18))
        if world.dash_ready <= 0:
            s.blit(self.font.render("dash ready", True, (180, 170, 150)), (WIDTH - 130, 46))

        if world.over:
            veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            veil.fill((0, 0, 0, 170))
            s.blit(veil, (0, 0))
            for text, font, y in (
                ("Your light went out", self.big, HEIGHT / 2 - 70),
                (f"Score {world.score}   survived {world.time:.0f}s   wave {world.wave}", self.font, HEIGHT / 2 + 10),
                ("Enter to burn again   Esc to quit", self.font, HEIGHT / 2 + 50),
            ):
                surf = font.render(text, True, TEXT)
                s.blit(surf, (WIDTH / 2 - surf.get_width() / 2, y))


def read_direction(keys) -> tuple[float, float]:
    dx = (keys[pygame.K_d] or keys[pygame.K_RIGHT]) - (keys[pygame.K_a] or keys[pygame.K_LEFT])
    dy = (keys[pygame.K_s] or keys[pygame.K_DOWN]) - (keys[pygame.K_w] or keys[pygame.K_UP])
    return float(dx), float(dy)


def main() -> None:
    pygame.init()
    pygame.display.set_caption("Lumen")
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()
    world = World()
    renderer = Renderer(screen)

    while True:
        dt = min(clock.tick(FPS) / 1000, 1 / 30)
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE):
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    world.dash(*read_direction(pygame.key.get_pressed()))
                if event.key == pygame.K_RETURN and world.over:
                    world.reset()
        world.update(dt, *read_direction(pygame.key.get_pressed()))
        renderer.draw(world)
        pygame.display.flip()


if __name__ == "__main__":
    main()
