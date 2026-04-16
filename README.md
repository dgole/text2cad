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
- **`_template/`** — Copy this to start a new project
- **`projects/`** — All projects live here
  - **`desk_organizer/`** — Desktop organizer with remote, pen, and phone slots
  - **`dust_port_adapter/`** — Clip-on adapter for Makita saw dust port

## Quick start

```bash
# Start a new project
cp -r _template/ projects/my_project/

# Generate STLs (from inside the project directory)
cd projects/dust_port_adapter
python profile_test.py
python profile_test.py --wall 3
```

See [AGENTS.md](AGENTS.md) for detailed conventions and workflow.
