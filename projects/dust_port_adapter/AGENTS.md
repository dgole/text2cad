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

### `adapter.py` — Complete adapter with curved transition tube

Builds the full adapter: faceplate + a single curved transition tube that
morphs from the irregular port hole to a circular hose connection while
simultaneously curving from vertical toward the exit direction. No discrete
elbow — the quad→circle morph and directional change happen together along
a smooth arc. Two stages:

- **`transition_test`** — Faceplate + curved transition (no socket).
  Verify the shape morph and curve look right.
- **`full`** — Complete adapter: faceplate + curved transition + female hose socket.

```
Side view (cross section):

    walls (open, clip onto saw rim)
    ┌───┐                 ┌───┐
    │   │  hollow inside  │   │
    ├───┴─────────────────┴───┤
    │█████████████████████████│  ← cap (with port hole + screw hole)
    ├─────────────────────────┤
    │  ╲                      │  ← curve starts immediately
    │    ╲  CURVED TRANSITION │    quad→circle morph happens
    │     ╲   (arc R=40mm)    │    along the arc path
    │      ╲                  │
    │       ○─────────────────│  ← now circular, ~75° from vertical
    │  SOCKET (20mm)          │  ← female, hose slides in
    └─────────────────────────┘

    Arc direction: 40° from A-D edge toward A-B edge
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
