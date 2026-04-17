# Fancy Pen Holder

## Description

A rectangular-prism pen holder with a separate lid. The base has
rectangular pen troughs cut into the top surface — pens rest in the
channels. There are two groups of slots:

- **Horizontal slots** — cylinder axis along +X (the long dimension).
- **Vertical slots** — cylinder axis along +Y (the short dimension).

Slot positions use a corner-origin coordinate system: (0,0) is the
bottom-left corner of the body footprint viewed from above.

The lid is a rectangular prism with the same XY footprint and magnet
pockets on its bottom face that align with the base's top-face pockets.

## Build stages

| Stage    | What it produces                              | What to check                              |
|----------|-----------------------------------------------|--------------------------------------------|
| `base`   | Base with pen slot troughs and magnet pockets  | Pens sit nicely; magnets seat flush        |
| `lid`    | Lid with bottom-face magnet pockets            | Sits flat on base; magnets align and hold  |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of
truth shared by all scripts in this project.
