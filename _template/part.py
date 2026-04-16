#!/usr/bin/env python3
"""
<Project Name> — <Part description>

Description:
    <Describe what this script produces and what it mates to.>

Usage:
    python part.py plate
    python part.py plate --example-param 45
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from cad.export import to_stl  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

# Pull values from CFG here, e.g.:
# WIDTH = CFG["width"]
# HEIGHT = CFG["height"]
# WALL = CFG["wall"]


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

# Define functions that return cadquery Workplane objects.
# Name them after what they produce — the CLI will pick them up from STAGES.
#
# def test_plate(width=WIDTH, height=HEIGHT, ...) -> cq.Workplane:
#     ...


# ---------------------------------------------------------------------------
# Stage registry — maps CLI names to builder functions
# ---------------------------------------------------------------------------

STAGES = {
    # "plate": test_plate,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("stage", choices=list(STAGES.keys()), help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))
    # <Add --flags for your parameters here so they're overridable.>
    # CLI flags override config values for one-off tweaks.
    args = parser.parse_args()

    builder = STAGES[args.stage]
    body = builder()
    name = f"{Path(__file__).parent.name}_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
