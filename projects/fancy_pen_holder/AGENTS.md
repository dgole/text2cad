# Fancy Pen Holder

## Description

A rectangular-prism pen holder with a separate lid. The base has
half-cylinder pen troughs cut into the top surface — pens rest in the
U-shaped channels. There are two groups of slots:

- **Horizontal slots** — cylinder axis along +X (the long dimension).
- **Vertical slots** — cylinder axis along +Y (the short dimension).

Slot positions use a corner-origin coordinate system: (0,0) is the
bottom-left corner of the body footprint viewed from above.

The lid is a plain rectangular prism with the same XY footprint.

## Build stages

| Stage    | What it produces                        | What to check                        |
|----------|-----------------------------------------|--------------------------------------|
| `block`  | Plain rectangular prism (base only)     | Overall size feels right             |
| `base`   | Base with pen slot troughs cut out      | Pens sit nicely in the half-cylinders|
| `lid`    | Lid piece (plain box, same XY footprint)| Sits flat on top of the base         |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of
truth shared by all scripts in this project.
