# Desk Organizer

## Description

Minimalist desktop / nightstand organizer — a rectangular prism with pockets
cut into it for TV remotes (2 rectangular from top), pens (3 circular from
top), and phones (2 thin slots from the front face).

## Reference

- Sketch from the human showing front, top, and side views.

## Build stages

| Stage     | What it produces                    | What to check                          |
|-----------|-------------------------------------|----------------------------------------|
| `block`   | Plain rectangular prism             | Overall size feels right on the desk   |
| `pockets` | Body + remote & pen pockets on top  | Pocket sizes fit remotes & pens        |
| `full`    | Complete part with phone slots      | Phone slides in/out of front slots     |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of truth.
CLI flags override config values for one-off tweaks.

| Key | Description |
|-----|-------------|
| `body.*` | Overall box dimensions, wall thickness, fillet |
| `remote_slots.*` | Count, pocket size, spacing, X offset |
| `pen_slots.*` | Count, diameter, spacing, X offset |
| `phone_slots.*` | Count, slot size, spacing, X/Z offset |
