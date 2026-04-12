# text2cad

Agent-assisted CAD for 3D printing. Describe a part conversationally, iterate
with test prints, get a parametric STL.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Structure

- **`cad/`** — Shared toolkit (profiles, operations, STL export)
- **`_template/`** — Copy this to start a new part project
- **`<part_name>/`** — Self-contained part: script, reference images, output STLs

## Quick start

```bash
# Start a new part
cp -r _template/ my_part/

# Generate an STL (from inside the part directory)
cd dust_port_adapter
python part.py plate
python part.py plate --port-width 45
```

See [AGENTS.md](AGENTS.md) for detailed conventions and workflow.
