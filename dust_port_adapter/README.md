# Dust Port Adapter

## Description

Clip-on adapter for a Makita circular saw dust exhaust port. The port has an
irregular quadrilateral flange/rim — not a simple rectangle. The adapter will
eventually clip onto this rim and connect to a dust collection hose.

## Status

**Early stage — working on the 2D profile of the outer rim flange.**

We have two scripts:
- `profile_test.py` — **active work.** Generates a thin outline matching the
  outer rim of the flange. This is the test piece to print and hold against
  the saw to verify the shape. Vertex coordinates define the inner edge
  (the surface that sits against the rim); the outer edge is offset outward
  by the wall thickness.
- `part.py` — original scaffolding with rectangular collar/mounting stages.
  **Not currently in use** — will be replaced or reworked once the 2D profile
  is nailed down and we move to the full 3D adapter.

## Reference

- `reference/saw_dust_port_exit_measurement_image.jpg` — photo of the dust port with measurement
- `reference/reference_part_for_inspo_real.webp` — photo of an existing dust port adapter for a smaller saw (design inspiration)
- `reference/reference_part_for_inspo_rendered.webp` — rendered view of the same inspiration part

## Current profile parameterization

The rim shape is an irregular quadrilateral with 4 mostly-straight sides.
Corner A (bottom-left) has significant rounding; the other 3 are near-90°.

```
        D -------- C
        |          |
         \         |
          A ------ B
```

Vertices define the **inner edge** (against the rim). All values in mm.

| Vertex | X | Y | Fillet | Notes |
|--------|------|------|--------|-------|
| A | 0 | 0 | 8.0 mm | Rounded corner |
| B | 63 | 30 | 2.5 mm | |
| C | 60 | 50 | 2.5 mm | |
| D | 10 | 50 | 2.5 mm | |

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WALL` | 2.5 mm | Frame wall thickness (added outward) |
| `THICKNESS` | 2.0 mm | Plate extrusion height (Z) |

**All vertex positions are rough estimates — need caliper measurements.**

## Next steps

1. Print `profile_test.py` outline, check fit against saw rim
2. Iterate on vertex positions and fillet radius until the inner edge matches
3. Study inspiration part references for the 3D adapter design (hose connection, clip mechanism)
4. Build the full 3D adapter

## Usage

```bash
cd dust_port_adapter
python profile_test.py
python profile_test.py --wall 3 --fillet-a 10
python profile_test.py --bx 68 --by 42
```
