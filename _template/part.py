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

import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import filleted_box, on_build_plate, safe_fillet_radius  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

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

# Define functions that return cadquery Workplane objects. Name them after
# what they produce — the CLI picks them up from STAGES.
#
# Stage builders receive only the parameters they declare, so each one can take
# just the arguments it cares about:
#
# def test_plate(width=WIDTH, height=HEIGHT) -> cq.Workplane:
#     return filleted_box(width, height, 3.0, fillet=2.0)


# ---------------------------------------------------------------------------
# Stage registry — maps CLI names to builder functions
# ---------------------------------------------------------------------------

STAGES = {
    # "plate": test_plate,
}


# ---------------------------------------------------------------------------
# CLI parameters — each becomes a --flag that overrides config for one run
# ---------------------------------------------------------------------------

# Entries take one of three forms:
#     "name": DEFAULT                        -> --name, parsed as a float
#     "name": (DEFAULT, "help text")         -> same, with help
#     "name": (DEFAULT, "help text", int)    -> explicit type (counts, etc.)
#
# Numbers default to float even when config.json stores them as an int, so a
# dimension written as `60` still accepts `--width 60.5`.

PARAMS = {
    # "width": (WIDTH, "Overall width (X)"),
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
