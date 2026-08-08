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

- **`cad/`** — Shared toolkit (CLI runner, geometry helpers, STL export)
- **`build.py`** — Builds every stage of every project; geometry regression check
- **`_template/`** — Copy this to start a new project
- **`projects/`** — All projects live here
  - **`desk_organizer/`** — Desktop organizer with remote, pen, and phone slots
  - **`door_hook/`** — Over-the-door hook with a projector platform
  - **`dust_port_adapter/`** — Clip-on adapter for Makita saw dust port
  - **`fancy_pen_holder/`** — Pen tray with a magnetic lid
  - **`interlocking_token_trays/`** — Stacking keyed token trays and a holder
  - **`rotating_bezel/`** — Magnetic detent ring pair
  - **`utility_card_sidecar/`** — Clip-on caddy for a utility cart

## Quick start

```bash
# Start a new project
cp -r _template/ projects/my_project/

# Generate STLs — scripts run from anywhere
python projects/dust_port_adapter/profile_test.py
python projects/dust_port_adapter/profile_test.py --wall 3

# Rebuild everything, or verify nothing changed
python build.py
python build.py --check
```

STLs land in each project's `output/`. Run `python viewer/server.py` and open
http://localhost:8321 to inspect them in 3D.

See [AGENTS.md](AGENTS.md) for detailed conventions and workflow.
