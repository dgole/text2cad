# Dust Port Adapter

## Description

Clip-on adapter for a Makita circular saw dust exhaust port. The port has an
irregular quadrilateral flange/rim — not a simple rectangle. The adapter
clips onto this rim and connects to a dust collection hose.

## Files

### `profile_test.py` — Rim profile test piece

Generates a thin outline (frame) matching the outer perimeter of the flange/rim.
Print it, hold it against the saw, check fit. This is the iterative measurement
tool — get the shape right here first.

### `faceplate.py` — Faceplate with walls

Builds the actual adapter body: walls that drop over the flange rim, capped with
a solid plate. The wall profile reuses the geometry from `profile_test.py`.
Includes a screw hole through the cap. Oriented cap-down for printing.

```
Side view (cross section):

    cap (flat on print bed)
    ┌─────────────────────────┐
    │█████████████████████████│  ← solid cap (with screw hole)
    ├───┐                 ┌───┤
    │   │  hollow inside  │   │  ← walls wrap around flange rim
    │   │                 │   │
    └───┘                 └───┘
```

`faceplate.py` imports geometry helpers from `profile_test.py` — they share a
single source of truth for the rim shape via `config.json`.

### `adapter.py` — Complete adapter with transition tube

Builds the full adapter: faceplate + transition tube that morphs from the
irregular port hole to a circular hose connection. Three stages:

- **`loft_test`** — Faceplate + straight transition loft (quad → circle).
  Verify the cross-section morph looks right.
- **`elbow_test`** — Faceplate + loft + 90° elbow.
  Check the bend geometry.
- **`full`** — Complete adapter: faceplate + loft + elbow + female hose socket.

```
Side view (cross section):

    walls (open, clip onto saw rim)
    ┌───┐                 ┌───┐
    │   │  hollow inside  │   │
    ├───┴─────────────────┴───┤
    │█████████████████████████│  ← cap (with port hole + screw hole)
    ├─────────────────────────┤
    │   TRANSITION LOFT       │  quad → circle, ~40mm
    │   (quad cross-section   │
    │    morphs to circle)    │
    ├────────○────────────────┤  ← now circular
    │         ╲               │
    │    90°   ╲  ELBOW       │  ~40mm bend radius
    │    bend   ╲             │
    ├────────────○            │
    │   SOCKET   │            │  ← female, hose slides in, ~20mm
    └────────────┘

    Bend direction: toward the A-D edge (left side of faceplate)
```

Imports `build_faceplate()` from `faceplate.py` and geometry helpers from
`profile_test.py`. All tube parameters live in `config.json` under `transition`.

## Reference

- `reference/saw_dust_port_exit_measurement_image.jpg` — photo of the dust port with measurement
- `reference/reference_part_for_inspo_real.webp` — photo of an existing dust port adapter for a smaller saw (design inspiration)
- `reference/reference_part_for_inspo_rendered.webp` — rendered view of the same inspiration part

## Rim shape

The rim is an irregular quadrilateral with 4 mostly-straight sides.
Corner A (bottom-left) has significant rounding; the other 3 are near-90°.

```
        D -------- C
        |          |
         \         |
          A ------ B
```

Vertices define the **inner edge** (against the rim).

## Parameters

All parameters live in [`config.json`](config.json) — the single source of truth.
CLI flags override config values for one-off tweaks.
