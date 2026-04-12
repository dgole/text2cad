# Agent Guide — text2cad

You are working in a project that generates parametric 3D-printable parts as
STL files using Python and cadquery. The human designs parts conversationally
with you: they provide reference photos, measurements, and intent; you write
bespoke parametric Python scripts that produce the geometry.

## Environment

- **Python virtual environment:** `.venv/` in the project root.
  Activate with `source .venv/bin/activate` before running anything.
- **CAD library:** [cadquery 2.5.2](https://cadquery.readthedocs.io/).
  All geometry is built with `cadquery.Workplane` objects.
- **Python version:** 3.9. Use `from __future__ import annotations` and
  `typing` module types (not `X | Y` syntax).
- **Units:** Everything is in **millimeters**.

## Project layout

```
text2cad/
├── cad/                    Shared toolkit — import from any part script
│   ├── profiles.py         2D profile generators (rounded_rect, circle, etc.)
│   ├── ops.py              Operations (add_screw_hole, add_lip, extrude)
│   └── export.py           to_stl() — writes Workplane → STL file
│
├── _template/              Skeleton for new part projects — copy, don't edit
│   ├── part.py             Annotated starter script
│   ├── README.md           Documentation template
│   ├── reference/          For photos
│   └── output/             For generated STLs
│
├── <part_name>/            One directory per part (self-contained)
│   ├── part.py             Bespoke parametric script for this part
│   ├── README.md           Part-specific docs, measurements, stage table
│   ├── reference/          Reference photos from the human
│   └── output/             Generated STL files
│
└── requirements.txt
```

## Creating a new part

1. Copy the template:
   ```bash
   cp -r _template/ <part_name>/
   ```
2. Put any reference images the human provides into `<part_name>/reference/`.
3. Edit `<part_name>/part.py` — this is the main deliverable. See conventions below.
4. Add a `<part_name>/README.md` documenting the part, its parameters, and build stages.

## Part script conventions

Look at `dust_port_adapter/part.py` as the canonical example. Key patterns:

### Imports and path setup
Every part.py starts with:
```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
```
This lets it import from `cad/` regardless of working directory.

### Parameters as module constants
Define all dimensions as named constants at the top of the file with comments.
These are the knobs the human will want to tweak:
```python
PORT_WIDTH = 42.0        # mm — wider dimension of port opening
PORT_HEIGHT = 28.0       # mm — shorter dimension
```

### Staged build functions
Design parts in testable stages — each stage is a function that returns a
`cq.Workplane` solid. Stages build on each other so the human can print
cheap test pieces early:

1. **Flat profile test** — a thin plate with the outline. Print it, hold it
   up to the real thing, check if the shape matches.
2. **Fit features** — add clips, lips, snap-fits. Print and test engagement.
3. **Mounting** — add screw holes, arms, brackets. Print and test alignment.
4. **Full part** — the complete geometry.

### Stage registry and CLI
```python
STAGES = {
    "plate": test_plate,
    "collar": test_collar,
}
```
The CLI uses argparse. Key dimensions should be exposed as `--flags` so the
human (or you) can override them without editing the file:
```bash
python part.py plate --port-width 45
```

### Running part scripts
Always run from the part directory (or specify the path):
```bash
cd dust_port_adapter && python part.py plate
```
STL files go into the part's own `output/` directory.

## Shared toolkit (`cad/`)

Use and extend these modules. If you find yourself writing something
reusable across parts, put it here.

### `cad/export.py`
- `to_stl(body, name, output_dir=None)` — export a Workplane to STL.
  Defaults output to the part's `output/` dir if you pass it.

### `cad/ops.py`
- `add_screw_hole(body, diameter, position, face_selector=">Z")` — cut a
  through-hole at an (x, y) position on a face.
- `add_lip(body, width, height, lip_depth, lip_thickness)` — add a clip lip
  ring around a rectangular opening.
- `extrude(workplane, height)` — simple extrude wrapper.

### `cad/profiles.py`
- `rounded_rect(width, height, fillet)` — 2D rounded rectangle.
- `circle(diameter)` — 2D circle.
- `rounded_rect_shell(outer_width, outer_height, wall, fillet)` — hollow
  rounded rectangle (for clip rings, rims).

## Design workflow with the human

1. **Photo & intent:** The human shows you a photo and describes what they
   want. Use your vision to identify shapes, features, and spatial
   relationships. You cannot extract exact dimensions from photos — ask the
   human to measure.

2. **Dimensions:** Get the human to measure critical interfaces with calipers
   or a ruler. These go into the parameters block. Use placeholder values and
   mark them clearly if measurements aren't available yet.

3. **Iterative test prints:** Start with the simplest stage (usually a flat
   plate outline). The human prints it, checks fit, reports back. You adjust
   parameters and regenerate. This is cheap and fast — don't try to get the
   full part right on the first attempt.

4. **Progressive stages:** Once the outline fits, move to the next stage
   (clips, mounting, full geometry). Each stage is a separate print-and-test
   cycle.

5. **Parameter tweaks:** When the human says "it's 2mm too wide", update the
   constant and regenerate. The script is the single source of truth.

## cadquery tips

- Fillet radius must be strictly less than half the smallest dimension of the
  face being filleted. Use `min(radius, dimension / 2 - 0.01)` to be safe.
- `edges("|Z")` selects edges parallel to Z — useful for filleting vertical
  edges of an extruded rectangle.
- Build solids by extruding 2D sketches and combining with `.union()` / `.cut()`.
- Negative extrude values go in the -Z direction.
- When in doubt, test your script by running it and checking that it produces
  a valid STL before telling the human it's ready.

## Git

Commit regularly. STL files are gitignored. Reference images are tracked.
Part scripts and READMEs are the important artifacts.
