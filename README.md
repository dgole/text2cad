# text2cad

Agent-assisted CAD tools. Take reference images, discuss dimensions conversationally,
generate parametric STL files for 3D printing.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Project structure

```
cad/            Core library modules
  profiles.py   Reusable 2D profile generators (rounded rects, circles, etc.)
  ops.py        Common CAD operations (extrude, screw holes, clip lips)
  export.py     STL export utilities

parts/          Part-specific scripts (one per project)
  dust_port_adapter.py   Circular saw dust port clip-on adapter

output/         Generated STL files (gitignored)
reference_images/   Photos of the thing you're designing for
```

## Usage

Part scripts double as CLI tools with overridable parameters:

```bash
# Generate a test plate with default dimensions
python -m parts.dust_port_adapter plate

# Override dimensions
python -m parts.dust_port_adapter plate --port-width 45 --port-height 30 --corner-radius 4

# Build stages: plate → collar → mounting → (full_adapter coming soon)
python -m parts.dust_port_adapter collar
python -m parts.dust_port_adapter mounting
```

## Workflow

1. Take a photo of the part you're mating to
2. Discuss with the agent — identify dimensions, constraints
3. Generate a test plate STL, print it, check fit
4. Adjust parameters, regenerate, reprint
5. Progress through build stages (plate → collar → mounting → full part)
