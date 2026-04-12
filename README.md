# text2cad

Agent-assisted CAD tools for 3D printing. Take reference photos, discuss
dimensions conversationally, generate parametric STL files.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project structure

```
cad/                Shared toolkit
  profiles.py       Reusable 2D profile generators
  ops.py            Common CAD operations (screw holes, clip lips, etc.)
  export.py         STL export utilities

_template/          Skeleton for new part projects
  part.py           Annotated starter script
  README.md         Part documentation template
  reference/        Reference photos
  output/           Generated STLs

dust_port_adapter/  Example: circular saw dust port clip-on adapter
  part.py           Parametric build script with staged outputs
  reference/        Photos of the saw port
  output/           Generated STLs
```

## Workflow

### Starting a new part

Copy `_template/` to a new directory and customize `part.py`:

```bash
cp -r _template/ my_new_part/
cd my_new_part/
# edit part.py — define parameters and build stages
```

### Iterating on a part

```bash
cd dust_port_adapter/

# Generate a test plate with default dimensions
python part.py plate

# Override dimensions from the command line
python part.py plate --port-width 45 --port-height 30

# Progress through stages as fit improves
python part.py collar
python part.py mounting
```

### Design loop

1. Take a photo of the thing you're designing for
2. Discuss with the agent — identify dimensions, constraints
3. Generate a test piece, print it, check fit
4. Adjust parameters, regenerate, reprint
5. Progress through build stages until the full part is done
