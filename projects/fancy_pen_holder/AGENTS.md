# Fancy Pen Holder

## Description

A rectangular-prism pen holder with a separate lid. The base has horizontal
half-cylinder pen slots cut into it — the cylinder axis runs along Y
(front-to-back), with the cylinder center sitting on the top edge of the
base so only the bottom half is material removal. Pens rest in the troughs.

The lid is a plain rectangular prism with the same XY footprint that sits
on top of the base.

## Reference

- Human description of overall dimensions and pen slot geometry.

## Build stages

| Stage    | What it produces                        | What to check                        |
|----------|-----------------------------------------|--------------------------------------|
| `block`  | Plain rectangular prism (base only)     | Overall size feels right             |
| `base`   | Base with pen slot troughs cut out      | Pens sit nicely in the half-cylinders|
| `lid`    | Lid piece (plain box, same XY footprint)| Sits flat on top of the base         |

## Parameters

All parameters live in [`config.json`](config.json) — the single source of
truth shared by all scripts in this project.
