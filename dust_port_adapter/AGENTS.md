# Dust Port Adapter

## Description

Clip-on adapter for a Makita circular saw dust exhaust port. The port has an
irregular quadrilateral flange/rim — not a simple rectangle. The adapter will
clip onto this rim and connect to a dust collection hose.

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

## Reference

- `reference/saw_dust_port_exit_measurement_image.jpg` — photo of the dust port with measurement
- `reference/reference_part_for_inspo_real.webp` — photo of an existing dust port adapter for a smaller saw (design inspiration)
- `reference/reference_part_for_inspo_rendered.webp` — rendered view of the same inspiration part

## Parameters

All parameters live in [`config.json`](config.json) — the single source of truth.
CLI flags override config values for one-off tweaks.

### Rim profile

The rim shape is an irregular quadrilateral with 4 mostly-straight sides.
Corner A (bottom-left) has significant rounding; the other 3 are near-90°.

```
        D -------- C
        |          |
         \         |
          A ------ B
```

Vertices define the **inner edge** (against the rim). All values in mm.

| Config key | Description |
|------------|-------------|
| `vertices.A` … `vertices.D` | Corner positions `[x, y]` |
| `fillets.A` … `fillets.D` | Fillet radius at each corner |
| `ab_bulge` | Inward curvature (sagitta) of the A→B edge. 0 = straight. |
| `wall` | Wall thickness (added outward from inner edge) |

### Profile test

| Config key | Description |
|------------|-------------|
| `profile_test.thickness` | Plate extrusion height (Z) for the test piece |

### Faceplate

| Config key | Description |
|------------|-------------|
| `faceplate.wall_height` | Height of the walls that wrap around the rim |
| `faceplate.cap_thickness` | Thickness of the solid cap |
| `faceplate.screw_x` | Screw hole center X coordinate |
| `faceplate.screw_y` | Screw hole center Y coordinate |
| `faceplate.screw_diameter` | Screw hole diameter |

**Vertex positions based on initial measurements — iterating on fit.**

## Usage

```bash
cd dust_port_adapter

# Profile test piece
python profile_test.py
python profile_test.py --wall 3 --fillet-a 10
python profile_test.py --bx 68 --by 42
python profile_test.py --ab-bulge 3

# Faceplate
python faceplate.py
python faceplate.py --wall-height 8 --cap-thickness 3
python faceplate.py --screw-diameter 1.5 --screw-x 14 --screw-y 54
```
