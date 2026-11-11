import math
import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")  # render without a window

import pygame

import lumen
from lumen import World


def test_light_burns_down_and_the_run_ends():
    world = World(seed=1)
    world.shadows.clear()
    for _ in range(60 * 60):
        world.update(1 / 60)
        if world.over:
            break
    assert world.over and world.light == 0


def test_collecting_a_mote_restores_light_and_scores():
    world = World(seed=1)
    world.shadows.clear()
    world.light = 50
    mote = world.motes[0]
    world.px, world.py = mote.x, mote.y
    world.update(0.001)
    assert world.score == 10
    assert world.light > 50
    assert len(world.motes) == 4  # a new one replaces it


def test_shadow_hit_drains_light_once_then_grants_safety():
    world = World(seed=1)
    world.shadows = [lumen.Shadow(world.px + 5, world.py, speed=0)]
    world.update(0.001)
    after_hit = world.light
    assert after_hit < lumen.LIGHT_START - lumen.SHADOW_DRAIN + 1
    world.shadows[0].x, world.shadows[0].y = world.px, world.py
    world.update(0.001)
    assert world.light > after_hit - 1  # invulnerable right after a hit


def test_dashing_through_a_shadow_is_safe():
    world = World(seed=1)
    world.shadows = [lumen.Shadow(world.px + 40, world.py, speed=0)]
    assert world.dash(1, 0)
    for _ in range(8):
        world.update(1 / 60)
    assert world.light > lumen.LIGHT_START - 2
    assert world.px > lumen.WIDTH / 2 + 60
    assert not world.dash(1, 0)  # on cooldown


def test_movement_stays_on_screen():
    world = World(seed=1)
    world.shadows.clear()
    for _ in range(300):
        world.update(1 / 60, -1, -1)
    assert world.px == lumen.PLAYER_RADIUS and world.py == lumen.PLAYER_RADIUS


def test_waves_add_shadows_over_time():
    world = World(seed=1)
    start = len(world.shadows)
    world.light = lumen.LIGHT_MAX
    world.time = 19.99
    world.shadows.clear()
    world.update(0.02)
    assert world.wave == 2 and len(world.shadows) == 4
    assert start == 3


def test_frames_render_headless(tmp_path):
    pygame.init()
    screen = pygame.display.set_mode((lumen.WIDTH, lumen.HEIGHT))
    world = World(seed=2)
    renderer = lumen.Renderer(screen)
    for i in range(120):
        world.update(1 / 60, math.cos(i / 20), math.sin(i / 20))
    renderer.draw(world)
    pygame.image.save(screen, str(tmp_path / "frame.png"))
    # Lit area around the player is brighter than the dark corner.
    center = screen.get_at((int(world.px), int(world.py)))
    corner = screen.get_at((2, lumen.HEIGHT - 2))
    assert sum(center[:3]) > sum(corner[:3]) + 200
    world.over = True
    renderer.draw(world)
    pygame.quit()
