# Lumen

A small survival game in Python and pygame. You are a lantern in a dark dungeon. Your
light burns down every second, and it is also how far you can see. Collect motes of
light to keep it burning while shadows close in from the dark. A shadow that touches
you drains your light; a quick dash slips straight through them.

The run ends when your light goes out. New shadows join every 20 seconds, and the
light burns faster the longer you last.

## Controls

| Key | Action |
|---|---|
| WASD or arrow keys | Move |
| Space | Dash in the direction you are moving (safe from shadows while dashing) |
| Enter | Play again after your light goes out |
| Esc | Quit |

## Run

Needs Python 3.9 or newer.

```bash
pip install -r requirements.txt
python lumen.py
```

## Test

```bash
pip install pytest
python -m pytest
```

The tests run without a window (SDL's dummy video driver). They cover the light timer,
collecting motes, shadow hits and the safety window after one, dashing through a
shadow, screen edges, waves, and rendering a frame where the lit area must be brighter
than the dark.

## How it works

- `World` holds every rule and has no drawing code, so it runs headless.
- The darkness is a full-screen layer with a soft radial hole cut at the lantern; the
  hole's size follows your light. A warm additive glow and a slight flicker sit on top.
- Motes are drawn above the darkness because they are light themselves. Shadows are
  drawn below it, so you only see them once they reach your light.
- Shadows steer toward you with a sideways wobble, so they curve in instead of moving
  in straight lines.
