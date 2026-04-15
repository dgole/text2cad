#!/usr/bin/env python3
"""
Part: Desk Organizer

Description:
    A minimalist desktop / nightstand organizer shaped as a rectangular prism.
    All features are subtractive — pockets cut from a solid block:
      - 2 TV remote slots (rectangular pockets cut from the top, left side)
      - 3 pen slots (circular holes cut from the top, right side)
      - 2 phone slots (horizontal slots cut through the side face at the
        bottom — phone lays flat, long axis along the organizer length)

    The top pockets are shallow enough that they don't intersect the
    phone slot zone at the bottom.

Usage:
    python part.py block          # Solid body only — check overall size
    python part.py pockets        # Body + top pockets (remotes & pens)
    python part.py full           # Complete part with phone slots

    python part.py full --width 180 --phone-gap 14
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add project root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parameters
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

# Body
BODY_WIDTH = CFG["body"]["width"]
BODY_DEPTH = CFG["body"]["depth"]
BODY_HEIGHT = CFG["body"]["height"]
BODY_WALL = CFG["body"]["wall"]
BODY_FILLET = CFG["body"]["fillet"]

# Remote slots (rectangular top pockets)
REMOTE_COUNT = CFG["remote_slots"]["count"]
REMOTE_WIDTH = CFG["remote_slots"]["width"]
REMOTE_DEPTH = CFG["remote_slots"]["depth"]
REMOTE_POCKET_DEPTH = CFG["remote_slots"]["pocket_depth"]
REMOTE_SPACING = CFG["remote_slots"]["spacing"]
REMOTE_FILLET = CFG["remote_slots"]["fillet"]
REMOTE_OFFSET_X = CFG["remote_slots"]["offset_x"]

# Pen slots (circular top pockets)
PEN_COUNT = CFG["pen_slots"]["count"]
PEN_DIAMETER = CFG["pen_slots"]["diameter"]
PEN_POCKET_DEPTH = CFG["pen_slots"]["pocket_depth"]
PEN_SPACING = CFG["pen_slots"]["spacing"]
PEN_OFFSET_X = CFG["pen_slots"]["offset_x"]

# Phone slots (horizontal openings on the side face)
# Phone lays flat, long axis along X. Opening is on one side face (X = +width/2).
PHONE_COUNT = CFG["phone_slots"]["count"]
PHONE_WIDTH = CFG["phone_slots"]["width"]              # Y span of the opening
PHONE_GAP = CFG["phone_slots"]["gap"]                  # Z height (thin gap)
PHONE_INTERIOR_LENGTH = CFG["phone_slots"]["interior_length"]  # X depth into body
PHONE_SPACING = CFG["phone_slots"]["spacing"]          # Z gap between stacked slots
PHONE_OFFSET_Y = CFG["phone_slots"]["offset_y"]       # Y offset of opening center
PHONE_OFFSET_Z = CFG["phone_slots"]["offset_z"]       # Z position of lowest slot


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def build_body(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    wall: float = BODY_WALL,
    fillet: float = BODY_FILLET,
) -> cq.Workplane:
    """
    Stage 1 — solid rectangular block with filleted vertical edges.
    Origin is at the center-bottom of the block (Z=0 is the base).
    """
    body = (
        cq.Workplane("XY")
        .box(width, depth, height, centered=(True, True, False))
    )
    safe_fillet = min(fillet, min(width, depth) / 2 - 0.01)
    if safe_fillet > 0.01:
        body = body.edges("|Z").fillet(safe_fillet)
    return body


def build_pockets(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    wall: float = BODY_WALL,
    fillet: float = BODY_FILLET,
    remote_count: int = REMOTE_COUNT,
    remote_width: float = REMOTE_WIDTH,
    remote_depth: float = REMOTE_DEPTH,
    remote_pocket_depth: float = REMOTE_POCKET_DEPTH,
    remote_spacing: float = REMOTE_SPACING,
    remote_fillet: float = REMOTE_FILLET,
    remote_offset_x: float = REMOTE_OFFSET_X,
    pen_count: int = PEN_COUNT,
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    pen_spacing: float = PEN_SPACING,
    pen_offset_x: float = PEN_OFFSET_X,
) -> cq.Workplane:
    """
    Stage 2 — body with remote pockets and pen holes cut from the top.

    Remote slots are rectangular pockets arranged side-by-side on the left.
    Pen slots are circular holes arranged in a column along Y on the right.
    Both are cut downward from the top face.
    """
    body = build_body(width, depth, height, wall, fillet)

    # --- Remote pockets (rectangular, cut from top) ---
    total_remotes_span = remote_count * remote_width + (remote_count - 1) * remote_spacing
    remote_start_x = remote_offset_x - total_remotes_span / 2 + remote_width / 2

    remote_positions = [
        (remote_start_x + i * (remote_width + remote_spacing), 0)
        for i in range(remote_count)
    ]

    safe_remote_fillet = min(remote_fillet, min(remote_width, remote_depth) / 2 - 0.01)

    for (rx, ry) in remote_positions:
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=height)
            .center(rx, ry)
            .rect(remote_width, remote_depth)
            .extrude(-remote_pocket_depth)
        )
        if safe_remote_fillet > 0.01:
            pocket = pocket.edges("|Z").fillet(safe_remote_fillet)
        body = body.cut(pocket)

    # --- Pen pockets (circular, cut from top) ---
    pen_start_y = -(pen_count - 1) * pen_spacing / 2

    pen_positions = [
        (pen_offset_x, pen_start_y + i * pen_spacing)
        for i in range(pen_count)
    ]

    for (px, py) in pen_positions:
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=height)
            .center(px, py)
            .circle(pen_diameter / 2)
            .extrude(-pen_pocket_depth)
        )
        body = body.cut(pocket)

    return body


def build_full(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    wall: float = BODY_WALL,
    fillet: float = BODY_FILLET,
    remote_count: int = REMOTE_COUNT,
    remote_width: float = REMOTE_WIDTH,
    remote_depth: float = REMOTE_DEPTH,
    remote_pocket_depth: float = REMOTE_POCKET_DEPTH,
    remote_spacing: float = REMOTE_SPACING,
    remote_fillet: float = REMOTE_FILLET,
    remote_offset_x: float = REMOTE_OFFSET_X,
    pen_count: int = PEN_COUNT,
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    pen_spacing: float = PEN_SPACING,
    pen_offset_x: float = PEN_OFFSET_X,
    phone_count: int = PHONE_COUNT,
    phone_width: float = PHONE_WIDTH,
    phone_gap: float = PHONE_GAP,
    phone_interior_length: float = PHONE_INTERIOR_LENGTH,
    phone_spacing: float = PHONE_SPACING,
    phone_offset_y: float = PHONE_OFFSET_Y,
    phone_offset_z: float = PHONE_OFFSET_Z,
) -> cq.Workplane:
    """
    Stage 3 — complete organizer with horizontal phone slots on the side.

    Phone slots are horizontal mail-slot openings on one side face (+X side).
    The phone lays flat with its long axis along X (the organizer's length):
      - phone_width wide in Y (slot opening width on the side face)
      - phone_gap tall in Z (thin horizontal gap)
      - phone_interior_length deep in X (how far the phone extends inside)
      - Slots are stacked vertically at the bottom, starting at phone_offset_z
    """
    body = build_pockets(
        width, depth, height, wall, fillet,
        remote_count, remote_width, remote_depth,
        remote_pocket_depth, remote_spacing, remote_fillet, remote_offset_x,
        pen_count, pen_diameter, pen_pocket_depth, pen_spacing, pen_offset_x,
    )

    # --- Phone slots (horizontal, stacked vertically, opening on +X side) ---
    # Each slot is a thin box:
    #   X = phone_interior_length (how far the phone extends into the body)
    #   Y = phone_width (opening width on the side face)
    #   Z = phone_gap (thin horizontal opening)
    # Positioned so the right edge of the cutter overshoots past the +X side
    # face to cleanly pierce the side wall.

    side_x = width / 2  # +X side face position
    overshoot = 1.0

    for i in range(phone_count):
        slot_z = phone_offset_z + i * (phone_gap + phone_spacing)

        # The cutter extends from (side_x + overshoot) back toward -X
        # by phone_interior_length.
        cutter_right_x = side_x + overshoot
        cutter_left_x = cutter_right_x - phone_interior_length - overshoot

        cutter_x_size = cutter_right_x - cutter_left_x
        cutter_center_x = (cutter_left_x + cutter_right_x) / 2

        slot = (
            cq.Workplane("XY")
            .box(cutter_x_size, phone_width, phone_gap,
                 centered=(True, True, False))
            .translate((cutter_center_x, phone_offset_y, slot_z))
        )
        body = body.cut(slot)

    return body


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "block": build_body,
    "pockets": build_pockets,
    "full": build_full,
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
    parser.add_argument("--width", type=float, default=BODY_WIDTH,
                        help="Overall body width (X)")
    parser.add_argument("--depth", type=float, default=BODY_DEPTH,
                        help="Overall body depth (Y)")
    parser.add_argument("--height", type=float, default=BODY_HEIGHT,
                        help="Overall body height (Z)")
    parser.add_argument("--wall", type=float, default=BODY_WALL,
                        help="Shell wall thickness")
    parser.add_argument("--fillet", type=float, default=BODY_FILLET,
                        help="Vertical edge fillet radius")

    # Remote slot overrides
    parser.add_argument("--remote-count", type=int, default=REMOTE_COUNT)
    parser.add_argument("--remote-width", type=float, default=REMOTE_WIDTH)
    parser.add_argument("--remote-depth", type=float, default=REMOTE_DEPTH)
    parser.add_argument("--remote-pocket-depth", type=float, default=REMOTE_POCKET_DEPTH)
    parser.add_argument("--remote-spacing", type=float, default=REMOTE_SPACING)

    # Pen slot overrides
    parser.add_argument("--pen-count", type=int, default=PEN_COUNT)
    parser.add_argument("--pen-diameter", type=float, default=PEN_DIAMETER)
    parser.add_argument("--pen-pocket-depth", type=float, default=PEN_POCKET_DEPTH)
    parser.add_argument("--pen-spacing", type=float, default=PEN_SPACING)

    # Phone slot overrides
    parser.add_argument("--phone-count", type=int, default=PHONE_COUNT)
    parser.add_argument("--phone-width", type=float, default=PHONE_WIDTH,
                        help="Width of slot opening on the side face (Y)")
    parser.add_argument("--phone-gap", type=float, default=PHONE_GAP,
                        help="Height of slot opening (Z) — phone thickness + clearance")
    parser.add_argument("--phone-interior-length", type=float, default=PHONE_INTERIOR_LENGTH,
                        help="How far the phone extends into the body (X)")

    args = parser.parse_args()

    stage = args.stage
    if stage == "block":
        body = build_body(
            width=args.width, depth=args.depth, height=args.height,
            wall=args.wall, fillet=args.fillet,
        )
    elif stage == "pockets":
        body = build_pockets(
            width=args.width, depth=args.depth, height=args.height,
            wall=args.wall, fillet=args.fillet,
            remote_count=args.remote_count,
            remote_width=args.remote_width,
            remote_depth=args.remote_depth,
            remote_pocket_depth=args.remote_pocket_depth,
            remote_spacing=args.remote_spacing,
            pen_count=args.pen_count,
            pen_diameter=args.pen_diameter,
            pen_pocket_depth=args.pen_pocket_depth,
            pen_spacing=args.pen_spacing,
        )
    elif stage == "full":
        body = build_full(
            width=args.width, depth=args.depth, height=args.height,
            wall=args.wall, fillet=args.fillet,
            remote_count=args.remote_count,
            remote_width=args.remote_width,
            remote_depth=args.remote_depth,
            remote_pocket_depth=args.remote_pocket_depth,
            remote_spacing=args.remote_spacing,
            pen_count=args.pen_count,
            pen_diameter=args.pen_diameter,
            pen_pocket_depth=args.pen_pocket_depth,
            pen_spacing=args.pen_spacing,
            phone_count=args.phone_count,
            phone_width=args.phone_width,
            phone_gap=args.phone_gap,
            phone_interior_length=args.phone_interior_length,
        )

    name = f"desk_organizer_{stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
