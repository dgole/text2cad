#!/usr/bin/env python3
"""
Part: Fancy Pen Holder — base tray + lid

Description:
    Base: a rectangular prism with horizontal half-cylinder pen troughs
    cut from the top.  Each trough's cylinder axis runs along Y (front
    to back).  The cylinder centre sits at the top surface of the base
    so only the bottom half is removed — pens rest in the resulting
    U-shaped channel.

    Lid: a plain rectangular prism with the same XY footprint.

Usage:
    python part.py block                # Solid base body — check size
    python part.py base                 # Base with pen troughs
    python part.py lid                  # Lid piece
    python part.py base --pen-diameter 12 --pen-spacing 35
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add repo root so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config
# ---------------------------------------------------------------------------

# Body (base)
BODY_WIDTH  = CFG["body"]["width"]
BODY_DEPTH  = CFG["body"]["depth"]
BODY_HEIGHT = CFG["body"]["height"]
BODY_FILLET = CFG["body"]["fillet"]

# Lid
LID_HEIGHT = CFG["lid"]["height"]

# Pen slots
PEN_COUNT       = CFG["pen_slots"]["count"]
PEN_DIAMETER    = CFG["pen_slots"]["diameter"]
PEN_SLOT_LENGTH = CFG["pen_slots"]["slot_length"]
PEN_SPACING     = CFG["pen_slots"]["spacing"]
PEN_OFFSET_X    = CFG["pen_slots"]["offset_x"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_box(
    width: float, depth: float, height: float, fillet: float,
) -> cq.Workplane:
    """Rectangular prism with filleted vertical edges, base at Z=0."""
    body = (
        cq.Workplane("XY")
        .box(width, depth, height, centered=(True, True, False))
    )
    safe_fillet = min(fillet, min(width, depth) / 2 - 0.01)
    if safe_fillet > 0.01:
        body = body.edges("|Z").fillet(safe_fillet)
    return body


def _cut_pen_troughs(
    body: cq.Workplane,
    body_height: float,
    body_depth: float,
    pen_count: int,
    pen_diameter: float,
    slot_length: float,
    spacing: float,
    offset_x: float,
) -> cq.Workplane:
    """
    Cut half-cylinder pen troughs into the top of *body*.

    Each trough is a cylinder whose axis runs along Y.  The cylinder's
    centre is at Z = body_height (the top surface), so only the bottom
    hemisphere of the cylinder intersects the body — producing a
    U-shaped channel that a pen can rest in.

    *slot_length* controls how long the trough is (along Y).  The
    trough is centred in Y on the body.
    """
    radius = pen_diameter / 2

    # X positions for each slot, centred as a group around offset_x
    total_span = (pen_count - 1) * spacing
    start_x = offset_x - total_span / 2

    for i in range(pen_count):
        cx = start_x + i * spacing

        # Build a cylinder oriented along Y, centred at (cx, 0, body_height)
        # Length = slot_length, radius = pen_diameter / 2
        cutter = (
            cq.Workplane("XZ")          # work in the XZ plane
            .center(cx, body_height)     # cylinder centre at top surface
            .circle(radius)
            .extrude(slot_length / 2)    # extrude in +Y
            .mirror("XZ", union=True)    # mirror to get -Y half too
        )
        body = body.cut(cutter)

    return body


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def build_block(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    **_kw,
) -> cq.Workplane:
    """Stage: solid base block — check overall size."""
    return _make_box(width, depth, height, fillet)


def build_base(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    pen_count: int = PEN_COUNT,
    pen_diameter: float = PEN_DIAMETER,
    slot_length: float = PEN_SLOT_LENGTH,
    pen_spacing: float = PEN_SPACING,
    pen_offset_x: float = PEN_OFFSET_X,
    **_kw,
) -> cq.Workplane:
    """Stage: base with half-cylinder pen troughs cut from the top."""
    body = _make_box(width, depth, height, fillet)
    body = _cut_pen_troughs(
        body, height, depth,
        pen_count, pen_diameter, slot_length, pen_spacing, pen_offset_x,
    )
    return body


def build_lid(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    lid_height: float = LID_HEIGHT,
    fillet: float = BODY_FILLET,
    **_kw,
) -> cq.Workplane:
    """Stage: lid — same XY footprint, shorter height."""
    return _make_box(width, depth, lid_height, fillet)


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "block": build_block,
    "base":  build_base,
    "lid":   build_lid,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("stage", choices=list(STAGES.keys()),
                        help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))

    # Body overrides
    parser.add_argument("--width",  type=float, default=BODY_WIDTH,
                        help="Body width (X)")
    parser.add_argument("--depth",  type=float, default=BODY_DEPTH,
                        help="Body depth (Y)")
    parser.add_argument("--height", type=float, default=BODY_HEIGHT,
                        help="Body height (Z)")
    parser.add_argument("--fillet", type=float, default=BODY_FILLET,
                        help="Vertical edge fillet radius")

    # Lid override
    parser.add_argument("--lid-height", type=float, default=LID_HEIGHT,
                        help="Lid height (Z)")

    # Pen-slot overrides
    parser.add_argument("--pen-count",    type=int,   default=PEN_COUNT,
                        help="Number of pen troughs")
    parser.add_argument("--pen-diameter", type=float, default=PEN_DIAMETER,
                        help="Diameter of the half-cylinder trough")
    parser.add_argument("--slot-length",  type=float, default=PEN_SLOT_LENGTH,
                        help="Length of each trough along Y")
    parser.add_argument("--pen-spacing",  type=float, default=PEN_SPACING,
                        help="Centre-to-centre spacing between troughs (X)")
    parser.add_argument("--pen-offset-x", type=float, default=PEN_OFFSET_X,
                        help="X offset of the trough group centre")

    args = parser.parse_args()

    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}

    body = STAGES[args.stage](**kw)
    name = f"fancy_pen_holder_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
