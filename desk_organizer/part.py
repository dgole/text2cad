#!/usr/bin/env python3
"""
Part: Desk Organizer

Description:
    A minimalist desktop / nightstand organizer shaped as a rectangular prism.
    All features are subtractive — pockets cut from a solid block:
      - 3 TV remote slots (rectangular pockets cut from the top, left side)
      - 3 pen slots (circular holes cut from the top, right side)
      - 2 phone slots (horizontal slots cut through the side face at the
        bottom — phone lays flat, long axis along the organizer length)

    For printability the body is split horizontally into two halves joined
    by printed alignment pins (dowel joint):
      - bottom half: phone slots + pin holes.  Print with phone openings
        facing up (rotated 90° so +X faces the sky).
      - top half: remote & pen pockets + pin holes.  Print upside-down so
        pocket openings face up (rotated 180°).
      - pegs: simple cylinders printed separately, pressed into holes on
        both halves during assembly.

Usage:
    python part.py block          # Solid body only — check overall size
    python part.py pockets        # Body + top pockets (remotes & pens)
    python part.py full           # Complete part (not printable as-is)
    python part.py bottom         # Printable bottom half (rotated for printing)
    python part.py top            # Printable top half (rotated for printing)
    python part.py peg            # Single alignment peg
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

# Split / alignment pins
SPLIT_Z = CFG["split"]["z"]
PIN_DIAMETER = CFG["split"]["pin_diameter"]
PIN_HEIGHT = CFG["split"]["pin_height"]
PIN_CLEARANCE = CFG["split"]["pin_clearance"]
PIN_INSET_X = CFG["split"]["pin_inset_x"]
PIN_INSET_Y = CFG["split"]["pin_inset_y"]

# Phone slots (horizontal openings on the side face)
PHONE_COUNT = CFG["phone_slots"]["count"]
PHONE_WIDTH = CFG["phone_slots"]["width"]
PHONE_GAP_BOTTOM = CFG["phone_slots"]["gap_bottom"]
PHONE_GAP_TOP = CFG["phone_slots"]["gap_top"]
PHONE_INTERIOR_LENGTH = CFG["phone_slots"]["interior_length"]
PHONE_SPACING = CFG["phone_slots"]["spacing"]
PHONE_OFFSET_Y = CFG["phone_slots"]["offset_y"]
PHONE_OFFSET_Z = CFG["phone_slots"]["offset_z"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pin_positions(width: float, depth: float,
                   inset_x: float, inset_y: float):
    """Return (x, y) positions for 4 alignment pins near the corners."""
    hx = width / 2 - inset_x
    hy = depth / 2 - inset_y
    return [(-hx, -hy), (-hx, hy), (hx, -hy), (hx, hy)]


def _make_box(width: float, depth: float, height: float,
              fillet: float) -> cq.Workplane:
    """Rectangular prism with filleted vertical edges, base at Z=0."""
    body = (
        cq.Workplane("XY")
        .box(width, depth, height, centered=(True, True, False))
    )
    safe_fillet = min(fillet, min(width, depth) / 2 - 0.01)
    if safe_fillet > 0.01:
        body = body.edges("|Z").fillet(safe_fillet)
    return body


def _cut_remote_pockets(
    body: cq.Workplane,
    top_z: float,
    remote_count: int, remote_width: float, remote_depth: float,
    remote_pocket_depth: float, remote_spacing: float,
    remote_fillet: float, remote_offset_x: float,
) -> cq.Workplane:
    """Cut rectangular remote pockets from the top face of *body*."""
    total_span = remote_count * remote_width + (remote_count - 1) * remote_spacing
    start_x = remote_offset_x - total_span / 2 + remote_width / 2

    safe_rf = min(remote_fillet, min(remote_width, remote_depth) / 2 - 0.01)

    for i in range(remote_count):
        rx = start_x + i * (remote_width + remote_spacing)
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=top_z)
            .center(rx, 0)
            .rect(remote_width, remote_depth)
            .extrude(-remote_pocket_depth)
        )
        if safe_rf > 0.01:
            pocket = pocket.edges("|Z").fillet(safe_rf)
        body = body.cut(pocket)
    return body


def _cut_pen_pockets(
    body: cq.Workplane,
    top_z: float,
    pen_count: int, pen_diameter: float,
    pen_pocket_depth: float, pen_spacing: float,
    pen_offset_x: float,
) -> cq.Workplane:
    """Cut circular pen pockets from the top face of *body*."""
    start_y = -(pen_count - 1) * pen_spacing / 2

    for i in range(pen_count):
        py = start_y + i * pen_spacing
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=top_z)
            .center(pen_offset_x, py)
            .circle(pen_diameter / 2)
            .extrude(-pen_pocket_depth)
        )
        body = body.cut(pocket)
    return body


def _cut_phone_slots(
    body: cq.Workplane,
    width: float,
    phone_count: int, phone_width: float,
    phone_gap_bottom: float, phone_gap_top: float,
    phone_interior_length: float, phone_spacing: float,
    phone_offset_y: float, phone_offset_z: float,
) -> cq.Workplane:
    """Cut horizontal phone slots from the +X side face of *body*."""
    side_x = width / 2
    overshoot = 1.0
    gaps = [phone_gap_bottom, phone_gap_top]

    slot_z = phone_offset_z
    for i in range(phone_count):
        gap = gaps[i] if i < len(gaps) else phone_gap_top

        cutter_right_x = side_x + overshoot
        cutter_left_x = cutter_right_x - phone_interior_length - overshoot
        cutter_x_size = cutter_right_x - cutter_left_x
        cutter_center_x = (cutter_left_x + cutter_right_x) / 2

        slot = (
            cq.Workplane("XY")
            .box(cutter_x_size, phone_width, gap,
                 centered=(True, True, False))
            .translate((cutter_center_x, phone_offset_y, slot_z))
        )
        body = body.cut(slot)
        slot_z += gap + phone_spacing

    return body


def _cut_pin_holes(
    body: cq.Workplane,
    face_z: float,
    depth_into_body: float,
    hole_diameter: float,
    width: float, depth: float,
    inset_x: float, inset_y: float,
) -> cq.Workplane:
    """Cut alignment pin holes into a face at *face_z*, going inward."""
    for (px, py) in _pin_positions(width, depth, inset_x, inset_y):
        hole = (
            cq.Workplane("XY")
            .workplane(offset=face_z)
            .center(px, py)
            .circle(hole_diameter / 2)
            .extrude(-depth_into_body)
        )
        body = body.cut(hole)
    return body


def _move_to_build_plate(body: cq.Workplane) -> cq.Workplane:
    """Translate body so its bounding box sits on Z=0."""
    bb = body.val().BoundingBox()
    if abs(bb.zmin) > 0.001:
        body = body.translate((0, 0, -bb.zmin))
    return body


# ---------------------------------------------------------------------------
# Build stages — reference / visualization
# ---------------------------------------------------------------------------

def build_body(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    **_kw,
) -> cq.Workplane:
    """Stage: solid rectangular block — check overall size."""
    return _make_box(width, depth, height, fillet)


def build_pockets(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
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
    **_kw,
) -> cq.Workplane:
    """Stage: body with remote & pen pockets cut from the top."""
    body = _make_box(width, depth, height, fillet)
    body = _cut_remote_pockets(
        body, height,
        remote_count, remote_width, remote_depth,
        remote_pocket_depth, remote_spacing, remote_fillet, remote_offset_x,
    )
    body = _cut_pen_pockets(
        body, height,
        pen_count, pen_diameter, pen_pocket_depth, pen_spacing, pen_offset_x,
    )
    return body


def build_full(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
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
    phone_gap_bottom: float = PHONE_GAP_BOTTOM,
    phone_gap_top: float = PHONE_GAP_TOP,
    phone_interior_length: float = PHONE_INTERIOR_LENGTH,
    phone_spacing: float = PHONE_SPACING,
    phone_offset_y: float = PHONE_OFFSET_Y,
    phone_offset_z: float = PHONE_OFFSET_Z,
    **_kw,
) -> cq.Workplane:
    """Stage: complete organizer (reference — not directly printable)."""
    body = build_pockets(
        width=width, depth=depth, height=height, fillet=fillet,
        remote_count=remote_count, remote_width=remote_width,
        remote_depth=remote_depth, remote_pocket_depth=remote_pocket_depth,
        remote_spacing=remote_spacing, remote_fillet=remote_fillet,
        remote_offset_x=remote_offset_x,
        pen_count=pen_count, pen_diameter=pen_diameter,
        pen_pocket_depth=pen_pocket_depth, pen_spacing=pen_spacing,
        pen_offset_x=pen_offset_x,
    )
    body = _cut_phone_slots(
        body, width,
        phone_count, phone_width, phone_gap_bottom, phone_gap_top,
        phone_interior_length, phone_spacing, phone_offset_y, phone_offset_z,
    )
    return body


# ---------------------------------------------------------------------------
# Build stages — printable parts
# ---------------------------------------------------------------------------

def build_bottom(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    fillet: float = BODY_FILLET,
    split_z: float = SPLIT_Z,
    pin_diameter: float = PIN_DIAMETER,
    pin_height: float = PIN_HEIGHT,
    pin_clearance: float = PIN_CLEARANCE,
    pin_inset_x: float = PIN_INSET_X,
    pin_inset_y: float = PIN_INSET_Y,
    phone_count: int = PHONE_COUNT,
    phone_width: float = PHONE_WIDTH,
    phone_gap_bottom: float = PHONE_GAP_BOTTOM,
    phone_gap_top: float = PHONE_GAP_TOP,
    phone_interior_length: float = PHONE_INTERIOR_LENGTH,
    phone_spacing: float = PHONE_SPACING,
    phone_offset_y: float = PHONE_OFFSET_Y,
    phone_offset_z: float = PHONE_OFFSET_Z,
    **_kw,
) -> cq.Workplane:
    """
    Printable bottom half — phone slots + alignment pin holes on the
    split face.

    Rotated 90° around the Y axis so the phone slot openings (+X face)
    point up.  Print in this orientation — no overhangs.
    """
    body = _make_box(width, depth, split_z, fillet)

    # Cut phone slots
    body = _cut_phone_slots(
        body, width,
        phone_count, phone_width, phone_gap_bottom, phone_gap_top,
        phone_interior_length, phone_spacing, phone_offset_y, phone_offset_z,
    )

    # Cut alignment pin holes on the split face (top, Z = split_z)
    hole_d = pin_diameter + pin_clearance
    pin_half_h = pin_height / 2
    body = _cut_pin_holes(
        body, split_z, pin_half_h, hole_d,
        width, depth, pin_inset_x, pin_inset_y,
    )

    # Rotate so phone openings (+X) face up: -90° around Y axis
    # (+X becomes +Z, +Z becomes -X)
    body = body.rotateAboutCenter((0, 1, 0), -90)
    body = _move_to_build_plate(body)

    return body


def build_top(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    split_z: float = SPLIT_Z,
    pin_diameter: float = PIN_DIAMETER,
    pin_height: float = PIN_HEIGHT,
    pin_clearance: float = PIN_CLEARANCE,
    pin_inset_x: float = PIN_INSET_X,
    pin_inset_y: float = PIN_INSET_Y,
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
    **_kw,
) -> cq.Workplane:
    """
    Printable top half — remote & pen pockets + alignment pin holes on
    the split face (bottom).

    Rotated 180° around the X axis so pocket openings face up and the
    split face (with pin holes) is on top.  Print in this orientation.
    """
    top_height = height - split_z
    body = _make_box(width, depth, top_height, fillet)

    # Cut remote & pen pockets from the top (which is at Z = top_height)
    body = _cut_remote_pockets(
        body, top_height,
        remote_count, remote_width, remote_depth,
        remote_pocket_depth, remote_spacing, remote_fillet, remote_offset_x,
    )
    body = _cut_pen_pockets(
        body, top_height,
        pen_count, pen_diameter, pen_pocket_depth, pen_spacing, pen_offset_x,
    )

    # Cut alignment pin holes on the split face (bottom, Z = 0)
    # Holes go upward from Z=0 into the body.
    hole_d = pin_diameter + pin_clearance
    pin_half_h = pin_height / 2
    for (px, py) in _pin_positions(width, depth, pin_inset_x, pin_inset_y):
        hole = (
            cq.Workplane("XY")
            .center(px, py)
            .circle(hole_d / 2)
            .extrude(pin_half_h)
        )
        body = body.cut(hole)

    # No rotation needed — pockets already open upward, pin holes on
    # the bottom face (build plate side).  Ready to print as-is.

    return body


def build_peg(
    pin_diameter: float = PIN_DIAMETER,
    pin_height: float = PIN_HEIGHT,
    **_kw,
) -> cq.Workplane:
    """
    Single alignment peg — a plain cylinder.

    Print 4 of these.  They press-fit into the holes on both halves.
    """
    return (
        cq.Workplane("XY")
        .circle(pin_diameter / 2)
        .extrude(pin_height)
    )


def build_pen_insert(
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    **_kw,
) -> cq.Workplane:
    """
    Cylindrical insert that sits inside a pen pocket.

    - Diameter is 10% smaller than the pen pocket diameter so it drops
      in with a loose fit.
    - Height is half the pen pocket depth.
    """
    insert_diameter = pen_diameter * 0.9
    insert_height = pen_pocket_depth / 2
    return (
        cq.Workplane("XY")
        .circle(insert_diameter / 2)
        .extrude(insert_height)
    )


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "block": build_body,
    "pockets": build_pockets,
    "full": build_full,
    "bottom": build_bottom,
    "top": build_top,
    "peg": build_peg,
    "pen_insert": build_pen_insert,
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

    # Split overrides
    parser.add_argument("--split-z", type=float, default=SPLIT_Z,
                        help="Z height where body splits into two halves")
    parser.add_argument("--pin-diameter", type=float, default=PIN_DIAMETER)
    parser.add_argument("--pin-height", type=float, default=PIN_HEIGHT)

    # Phone slot overrides
    parser.add_argument("--phone-count", type=int, default=PHONE_COUNT)
    parser.add_argument("--phone-width", type=float, default=PHONE_WIDTH,
                        help="Width of slot opening on the side face (Y)")
    parser.add_argument("--phone-gap-bottom", type=float, default=PHONE_GAP_BOTTOM,
                        help="Height of bottom slot opening (Z)")
    parser.add_argument("--phone-gap-top", type=float, default=PHONE_GAP_TOP,
                        help="Height of top slot opening (Z)")
    parser.add_argument("--phone-interior-length", type=float, default=PHONE_INTERIOR_LENGTH,
                        help="How far the phone extends into the body (X)")

    args = parser.parse_args()

    # Build a kwargs dict from all CLI args — stage functions use **_kw to
    # ignore parameters they don't care about.
    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}

    body = STAGES[args.stage](**kw)

    name = f"desk_organizer_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
