# Interlocking Token Trays

## Description

Parametric interlocking trays for organizing tokens, tiles, or small game
components. The design includes interior dividers, interlocking
tab/slot features for stacking or tiling trays together, and optional lids.

A **holder** stores a vertical stack of trays (default: 8) in a simple
rectangular box with finger-relief cutouts for easy tray removal.

## Reference

No reference images yet.

## Parts

### `part.py` — Token Tray

| Stage        | What it produces                     | What to check                |
|--------------|--------------------------------------|------------------------------|
| `block`      | Solid rectangular prism              | Overall footprint & height   |
| `tray`       | Hollowed tray with magnet pockets    | Wall thickness, pocket fit   |
| `tray_keyed` | Tray with ridge/groove keying        | Interlocking alignment       |
| `tray_bottom`| Lower half (below pause Z)           | Magnet pocket visibility     |
| `tray_top`   | Upper half (above pause Z)           | Sealing cap fit              |

### `holder.py` — Stack Holder

| Stage    | What it produces                          | What to check               |
|----------|-------------------------------------------|------------------------------|
| `shell`  | Open-top rectangular box                  | Tray fitment, wall clearance |
| `holder` | Shell + finger-relief cutouts on ±Y walls | Grip access, edge finish     |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of
truth shared by all scripts in this project. `config.json` is self-documenting
via its key names and `_key` comments. Do not duplicate parameter values or
detailed key descriptions here.
CLI flags override config values for one-off tweaks.

