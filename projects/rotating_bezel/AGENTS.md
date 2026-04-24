# Rotating Bezel

## Description

Two stacked rings with embedded disc magnets that create a magnetic detent
mechanism. The rings snap together through magnetic attraction and can be
rotated relative to each other by overcoming the magnetic force, clicking
into the next aligned position.

Prototype / fidget-toy stage — may evolve toward a watch bezel.

## Reference

No reference images yet — pure parametric prototype.

- Magnets: 5×2 mm neodymium disc magnets
- 12 detent positions (30° spacing)
- Uniform polarity: all magnets in Ring A face N-up, Ring B face S-up

## Build stages

| Stage | What it produces | What to check |
|-------|-----------------|---------------|
| `ring` | Single ring with magnet pockets | Pocket fit for magnets, overall ring dimensions |
| `pair` | Both rings exported side-by-side | Print both, insert magnets, test snap & rotation feel |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of
truth shared by all scripts in this project. `config.json` is self-documenting
via its key names and `_key` comments. Do not duplicate parameter values or
detailed key descriptions here.
CLI flags override config values for one-off tweaks.
