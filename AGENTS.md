# Agent Guide — text2cad

You are working in a repo that generates parametric 3D-printable parts as
STL files using Python and cadquery. The human designs parts conversationally
with you: they provide reference photos, measurements, and intent; you write
bespoke parametric Python scripts that produce the geometry.

A **project** is a self-contained directory for a design effort — it may
produce multiple related parts (e.g. a top half, bottom half, and alignment
pegs). All parts in a project share a single `config.json` so they stay
self-consistent when parameters change.

## Environment

- **Python virtual environment:** `.venv/` in the repo root.
  Activate with `source .venv/bin/activate` before running anything.
- **CAD library:** [cadquery 2.5.2](https://cadquery.readthedocs.io/).
  All geometry is built with `cadquery.Workplane` objects.
- **Python version:** 3.9. Use `from __future__ import annotations` and
  `typing` module types (not `X | Y` syntax).
- **Units:** Everything is in **millimeters**.

## Repo layout

```
text2cad/
├── cad/                    Shared toolkit — import from any project script
│   ├── profiles.py         2D profile generators (rounded_rect, circle, etc.)
│   ├── ops.py              Operations (add_screw_hole, add_lip, extrude)
│   └── export.py           to_stl() — writes Workplane → STL file
│
├── _template/              Skeleton for new projects — copy, don't edit
│   ├── config.json         Parameter defaults (single source of truth)
│   ├── part.py             Annotated starter script
│   ├── AGENTS.md           Documentation template
│   ├── reference/          For photos
│   └── output/             For generated STLs
│
├── projects/               All projects live here
│   └── <project_name>/     One directory per project (self-contained)
│       ├── config.json     Shared parameters for all parts in this project
│       ├── *.py            One or more scripts — each produces part STLs
│       ├── AGENTS.md       Project description, build stages, references
│       ├── reference/      Reference photos from the human
│       └── output/         Generated STL files
│
└── requirements.txt
```

## Creating a new project

1. Copy the template:
   ```bash
   cp -r _template/ projects/<project_name>/
   ```
2. Put any reference images the human provides into `projects/<project_name>/reference/`.
3. Edit/add Python scripts in the project directory. See conventions below.
4. Fill in `projects/<project_name>/AGENTS.md` with the project description, build stages, and references.

## Script conventions

Look at `projects/desk_organizer/part.py` as the canonical example (it uses
staged builds, a `STAGES` registry, and argparse CLI overrides). Key patterns:

### Imports and path setup
Every script starts with:
```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
```
This lets it import from `cad/` regardless of working directory (project
scripts live two levels below the repo root: `projects/<project_name>/`).

### Parameters via config.json
Each project has a single `config.json` — the single source of truth for all
dimensions across every part in the project. Scripts load it at startup and
expose module-level constants:
```python
_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

PORT_WIDTH = CFG["port_width"]     # mm
PORT_HEIGHT = CFG["port_height"]   # mm
```
When a parameter changes, edit `config.json` once — all scripts in the
project pick it up. This is what keeps multiple related parts self-consistent.
CLI flags still override config values for one-off tweaks.

**`config.json` is self-documenting** — use clear, descriptive key names so
the file speaks for itself. Do not duplicate parameter names, descriptions,
or values in AGENTS.md or anywhere else. That just creates multiple places
to update every time a parameter changes.

For keys where the name alone isn't enough, add a `_key` comment entry
directly above it in the JSON:
```json
{
    "_ab_bulge": "Inward curvature (sagitta) of the A-B edge. 0 = straight.",
    "ab_bulge": 3.0
}
```
Use `_comment` for section-level context. Only comment what isn't obvious
from the key name — don't over-annotate.

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

### Multiple scripts per project
A project can have more than one script when it makes sense — for example,
`dust_port_adapter` has `profile_test.py` (test piece) and `faceplate.py`
(the actual adapter). All scripts in a project share the same `config.json`.

### Running scripts
Always run from the project directory (or specify the path):
```bash
cd projects/dust_port_adapter && python profile_test.py
```
STL files go into the project's `output/` directory.

## Shared toolkit (`cad/`)

Use and extend these modules. If you find yourself writing something
reusable across projects, put it here.

### `cad/export.py`
- `to_stl(body, name, output_dir=None)` — export a Workplane to STL.
  Defaults output to the caller's `output/` dir if you pass it.

### `cad/ops.py`
- `add_screw_hole(body, diameter, position, face_selector=">Z")` — cut a
  through-hole at an (x, y) position on a face.
- `add_lip(body, width, height, lip_depth, lip_thickness)` — add a clip lip
  ring around a rectangular opening.

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
   or a ruler. These go into `config.json`. Use placeholder values and
   mark them clearly if measurements aren't available yet.

3. **Iterative test prints:** Start with the simplest stage (usually a flat
   plate outline). The human prints it, checks fit, reports back. You adjust
   parameters and regenerate. This is cheap and fast — don't try to get the
   full part right on the first attempt.

4. **Progressive stages:** Once the outline fits, move to the next stage
   (clips, mounting, full geometry). Each stage is a separate print-and-test
   cycle.

5. **Parameter tweaks:** When the human says "it's 2mm too wide", update
   `config.json` and regenerate. The config file is the single source of truth.

## cadquery tips

- Fillet radius must be strictly less than half the smallest dimension of the
  face being filleted. Use `min(radius, dimension / 2 - 0.01)` to be safe.
- `edges("|Z")` selects edges parallel to Z — useful for filleting vertical
  edges of an extruded rectangle.
- Build solids by extruding 2D sketches and combining with `.union()` / `.cut()`.
- Negative extrude values go in the -Z direction.
- When in doubt, test your script by running it and checking that it produces
  a valid STL before telling the human it's ready.

## STL Viewer

Run `python viewer/server.py` and open http://localhost:8321 to visually inspect generated STL files in a 3D viewport.

## Git

Commit regularly. STL files are gitignored. Reference images are tracked.
Project scripts and AGENTS.md files are the important artifacts.
