# Desk Organizer

## Description

Minimalist desktop / nightstand organizer — a rectangular prism with pockets
cut into it for TV remotes (rectangular from top), pens (circular from top),
and phones (thin slots from the front face).

For printability the body is split horizontally into two halves joined by
alignment pins (dowel joint).

## Reference

- Sketch from the human showing front, top, and side views.

## Build stages

| Stage     | What it produces                         | What to check                              |
|-----------|------------------------------------------|--------------------------------------------|
| `block`   | Plain rectangular prism                  | Overall size feels right on the desk       |
| `pockets` | Body + remote & pen pockets on top       | Pocket sizes fit remotes & pens            |
| `full`    | Complete part with phone slots           | Phone slides in/out of side slots          |
| `bottom`  | Printable bottom half (rotated)          | Phone slots open upward, pin holes visible |
| `top`     | Printable top half (flipped)             | Pockets open upward, pin holes visible     |
| `peg`     | Single alignment peg                     | Print 4 of these                           |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of truth.
CLI flags override config values for one-off tweaks.
