#!/usr/bin/env python3
"""
Part: Fancy Pen Holder — base tray + lid

Description:
    Base: a rectangular prism with horizontal half-cylinder pen troughs
    cut from the top.  Each trough's cylinder axis runs along X (left
    to right — the long axis).  The cylinder centre sits at the top
    surface of the base so only the bottom half is removed — pens rest
    in the resulting U-shaped channel.

    Lid: a plain rectangular prism with the same XY footprint.

Usage:
    python part.py block                # Solid base body — check size
    python part.py base                 # Base with pen troughs
    python part.py lid                  # Lid piece
    python part.py base --width 180      # override body width
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

# Pen slots — horizontal (axis along +X) and vertical (axis along +Y)
H_SLOTS = CFG["horizontal_slots"]
V_SLOTS = CFG["vertical_slots"]


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
    body_width: float,
    body_depth: float,
    body_height: float,
    h_slots: list,
    v_slots: list,
) -> cq.Workplane:
    """
    Cut half-cylinder pen troughs into the top of *body*.

    The body box is centered at the CQ origin, but slots use a
    corner-origin coordinate system where (0, 0) is the bottom-left
    corner of the footprint (min-X, min-Y when viewed from above).

    Each slot dict has: start_x, start_y, length, diameter.
    Horizontal slots run along +X; vertical slots run along +Y.
    The cylinder center sits at Z = body_height (the top surface) so
    only the bottom half is material removal.
    """
    # Corner-origin to CQ-centered offset
    ox = -body_width / 2
    oy = -body_depth / 2

    # --- Horizontal slots (axis along +X) ---
    for slot in h_slots:
        sx = slot["start_x"]
        sy = slot["start_y"]
        length = slot["length"]
        radius = slot["diameter"] / 2

        cx_start = ox + sx
        cy = oy + sy

        cutter = (
            cq.Workplane("YZ")
            .center(cy, body_height)
            .circle(radius)
            .extrude(length)
        )
        cutter = cutter.translate((cx_start, 0, 0))
        body = body.cut(cutter)

    # --- Vertical slots (axis along +Y) ---
    for slot in v_slots:
        sx = slot["start_x"]
        sy = slot["start_y"]
        length = slot["length"]
        radius = slot["diameter"] / 2

        cx = ox + sx
        cy_start = oy + sy

        cutter = (
            cq.Workplane("XZ")
            .center(cx, body_height)
            .circle(radius)
            .extrude(length)
        )
        cutter = cutter.translate((0, cy_start, 0))
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
    h_slots: list = H_SLOTS,
    v_slots: list = V_SLOTS,
    **_kw,
) -> cq.Workplane:
    """Stage: base with half-cylinder pen troughs cut from the top."""
    body = _make_box(width, depth, height, fillet)
    body = _cut_pen_troughs(body, width, depth, height, h_slots, v_slots)
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

    # Pen slots are defined in config.json (list of slot dicts).
    # No CLI overrides — edit config.json to add/move/resize slots.

    args = parser.parse_args()

    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}

    body = STAGES[args.stage](**kw)
    name = f"fancy_pen_holder_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
