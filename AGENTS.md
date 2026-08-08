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
│   ├── cli.py              load_config() + run() — the script entry point
│   ├── geometry.py         Shared geometry helpers
│   └── export.py           to_stl() — writes Workplane → STL file
│
├── build.py                Builds every stage of every project; regression check
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

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
```
This lets it import from `cad/` regardless of working directory (project
scripts live two levels below the repo root: `projects/<project_name>/`).

### Parameters via config.json
Each project has a single `config.json` — the single source of truth for all
dimensions across every part in the project. Scripts load it at startup and
expose module-level constants:
```python
CFG = load_config(__file__)

PORT_WIDTH = CFG["port_width"]     # mm
PORT_HEIGHT = CFG["port_height"]   # mm
```
When a parameter changes, edit `config.json` once — all scripts in the
project pick it up. This is what keeps multiple related parts self-consistent.
CLI flags still override config values for one-off tweaks.

Read config values with `CFG["key"]`, not `CFG.get("key", fallback)`. A
fallback is a second place the value lives, and the two drift apart — when
that happened here the code said 2.0 while the config said 5.0. If a key is
missing, the script should fail loudly.

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
Scripts do not write their own `main()`. Declare a stage registry and a params
dict, and hand both to `run()`:
```python
STAGES = {
    "plate": test_plate,
    "collar": test_collar,
}

PARAMS = {
    "port_width": (PORT_WIDTH, "Width of the port opening"),
    "slot_count": (SLOT_COUNT, "Number of slots", int),
}

if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
```
Each params entry becomes a `--flag` so the human (or you) can override a
dimension without editing the file:
```bash
python part.py plate --port-width 45
```
Entries take one of three forms — `DEFAULT`, `(DEFAULT, "help")`, or
`(DEFAULT, "help", type)`. Numbers are parsed as `float` unless you say
otherwise, because config.json often stores a dimension as a bare int and
`--port-width 45.5` must still work. Counts should pass `int` explicitly.

`run()` passes each stage builder only the parameters its signature declares,
so a builder can take just the arguments it cares about.

Output is always written to `output/<project_name>_<stage>.stl`. Don't
hand-name STL files — two scripts in a project that pick the same name will
overwrite each other, and `build.py` treats that as an error.

### Multiple scripts per project
A project can have more than one script when it makes sense — for example,
`dust_port_adapter` has `profile_test.py` (test piece) and `faceplate.py`
(the actual adapter). All scripts in a project share the same `config.json`.

### Running scripts
Scripts work from anywhere — run them by path or from inside the project:
```bash
python projects/dust_port_adapter/profile_test.py
```
STL files go into the project's `output/` directory.

### Building everything (`build.py`)
`build.py` builds every stage of every project — 29 stages in about 25s.

```bash
python build.py                  # rebuild everything
python build.py desk_organizer   # just one project
python build.py --check          # verify nothing changed geometrically
python build.py --snapshot       # record the current geometry as the baseline
```

**Run `--check` after touching anything in `cad/`.** Those modules are imported
by every project, so a change can break geometry in a project you weren't
thinking about. `--check` compares triangle count, volume, surface area, and
absolute bounding box against `build_baseline.json`, so it catches both a
changed shape and a part that has drifted off the build plate.

When you change a part *on purpose*, `--check` will report it — confirm the
reported deltas are the ones you intended, then re-run `--snapshot` to accept
them. Commit the updated baseline with the change.

## Shared toolkit (`cad/`)

### `cad/cli.py`
- `load_config(__file__)` — load the project's `config.json`.
- `run(__file__, STAGES, PARAMS)` — the whole CLI. See above.

### `cad/export.py`
- `to_stl(body, name, output_dir)` — export a Workplane to STL. `run()` calls
  this for you; call it directly only if you need a second output from one stage.

### `cad/geometry.py`
- `filleted_box(width, depth, height, fillet)` — rectangular prism with
  filleted vertical edges, centered in XY with its base on Z=0.
- `on_build_plate(body)` — translate a body so its lowest point sits on Z=0.
  A no-op if it already does, so it's safe to apply at the end of any stage.
- `safe_fillet_radius(radius, *spans)` — clamp a fillet to what the geometry
  can accept. Returns a value that may be <= 0, meaning "skip the fillet".

**Only add to `cad/` once something is genuinely duplicated.** This directory
previously held two modules of plausible-looking helpers that no project ever
imported, while the same three helpers were copy-pasted across ten scripts.
Write it inline first; promote it when the second project needs it.

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

Commit regularly. STL and 3MF files are gitignored. Reference images are
tracked. Project scripts, `config.json`, AGENTS.md files, and
`build_baseline.json` are the important artifacts.
