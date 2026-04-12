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

`faceplate.py` imports geometry helpers and default vertex coordinates from
`profile_test.py` — they share a single source of truth for the rim shape.

## Reference

- `reference/saw_dust_port_exit_measurement_image.jpg` — photo of the dust port with measurement
- `reference/reference_part_for_inspo_real.webp` — photo of an existing dust port adapter for a smaller saw (design inspiration)
- `reference/reference_part_for_inspo_rendered.webp` — rendered view of the same inspiration part

## Rim profile parameterization

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
| A | 0 | 0 | 7.5 mm | Rounded corner |
| B | 74 | 38 | 2.0 mm | |
| C | 70.5 | 58 | 2.0 mm | |
| D | 10 | 58 | 2.0 mm | |

### Profile parameters (shared)

| Parameter | Default | Description |
|-----------|---------|-------------|
| `AB_BULGE` | 4.0 mm | Inward curvature (sagitta) of the A→B edge. 0 = straight; positive = bows inward. |
| `WALL` | 4.0 mm | Wall thickness (added outward from inner edge) |

### Profile test parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `THICKNESS` | 2.0 mm | Plate extrusion height (Z) for the test piece |

### Faceplate parameters

| Parameter | Default | Description |
|-----------|---------|-------------|
| `WALL_HEIGHT` | 6.0 mm | Height of the walls that wrap around the rim |
| `CAP_THICKNESS` | 2.0 mm | Thickness of the solid cap |
| `SCREW_X` | 12.0 mm | Screw hole center X coordinate |
| `SCREW_Y` | 56.0 mm | Screw hole center Y coordinate |
| `SCREW_DIAMETER` | 1.2 mm | Screw hole diameter |

**Vertex positions based on initial measurements — iterating on fit.**

## Next steps

1. ~~Print `profile_test.py` outline, check fit against saw rim~~
2. Iterate on vertex positions and fillet radii until the inner edge matches
3. Cut the dust port opening in the faceplate cap
4. Design the hose connection (tube/funnel extending from the port opening)
5. Add clip mechanism to hold the adapter onto the rim

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
