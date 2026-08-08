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

import sys
from pathlib import Path

# Add project root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import filleted_box, on_build_plate, safe_fillet_radius  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parameters
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

# Body
BODY_WIDTH = CFG["body"]["width"]
BODY_DEPTH = CFG["body"]["depth"]
BODY_HEIGHT = CFG["body"]["height"]
BODY_WALL = CFG["body"]["wall"]
BODY_FILLET = CFG["body"]["fillet"]

# Remote slots — long
REMOTE_LONG_COUNT = CFG["remote_slots_long"]["count"]
REMOTE_LONG_WIDTH = CFG["remote_slots_long"]["width"]
REMOTE_LONG_DEPTH = CFG["remote_slots_long"]["depth"]
REMOTE_LONG_POCKET_DEPTH = CFG["remote_slots_long"]["pocket_depth"]
REMOTE_LONG_FILLET = CFG["remote_slots_long"]["fillet"]

# Remote slots — short
REMOTE_SHORT_COUNT = CFG["remote_slots_short"]["count"]
REMOTE_SHORT_WIDTH = CFG["remote_slots_short"]["width"]
REMOTE_SHORT_DEPTH = CFG["remote_slots_short"]["depth"]
REMOTE_SHORT_POCKET_DEPTH = CFG["remote_slots_short"]["pocket_depth"]
REMOTE_SHORT_FILLET = CFG["remote_slots_short"]["fillet"]

# Remote layout (shared)
REMOTE_SPACING = CFG["remote_layout"]["spacing"]
REMOTE_OFFSET_X = CFG["remote_layout"]["offset_x"]

# Pen slots (circular top pockets)
PEN_DIAMETER = CFG["pen_slots"]["diameter"]
PEN_POCKET_DEPTH = CFG["pen_slots"]["pocket_depth"]
PEN_POSITIONS = [tuple(p) for p in CFG["pen_slots"]["positions"]]

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


def _cut_remote_pockets(
    body: cq.Workplane,
    top_z: float,
    remote_long_count: int, remote_long_width: float, remote_long_depth: float,
    remote_long_pocket_depth: float, remote_long_fillet: float,
    remote_short_count: int, remote_short_width: float, remote_short_depth: float,
    remote_short_pocket_depth: float, remote_short_fillet: float,
    remote_spacing: float, remote_offset_x: float,
) -> cq.Workplane:
    """Cut long and short rectangular remote pockets from the top face.

    Long slots are laid out first (leftmost), then short slots to their right.
    The whole group is centered on *remote_offset_x*.
    """
    # Build a list of (width, depth, pocket_depth, fillet) for each slot
    slots = (
        [(remote_long_width, remote_long_depth, remote_long_pocket_depth, remote_long_fillet)] * remote_long_count
        + [(remote_short_width, remote_short_depth, remote_short_pocket_depth, remote_short_fillet)] * remote_short_count
    )
    total_count = len(slots)
    if total_count == 0:
        return body

    # All slots use the same width for X-spacing purposes
    widths = [s[0] for s in slots]
    total_span = sum(widths) + (total_count - 1) * remote_spacing

    # X position of the left edge of the first slot
    cursor_x = remote_offset_x - total_span / 2

    for (sw, sd, spd, sf) in slots:
        rx = cursor_x + sw / 2  # center of this slot
        safe_rf = safe_fillet_radius(sf, sw, sd)
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=top_z)
            .center(rx, 0)
            .rect(sw, sd)
            .extrude(-spd)
        )
        if safe_rf > 0.01:
            pocket = pocket.edges("|Z").fillet(safe_rf)
        body = body.cut(pocket)
        cursor_x += sw + remote_spacing

    return body


def _cut_pen_pockets(
    body: cq.Workplane,
    top_z: float,
    pen_diameter: float,
    pen_pocket_depth: float,
    pen_positions: list,
) -> cq.Workplane:
    """Cut circular pen pockets from the top face at explicit (x, y) positions."""
    for (px, py) in pen_positions:
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=top_z)
            .center(px, py)
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
    return filleted_box(width, depth, height, fillet)


def build_pockets(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    remote_long_count: int = REMOTE_LONG_COUNT,
    remote_long_width: float = REMOTE_LONG_WIDTH,
    remote_long_depth: float = REMOTE_LONG_DEPTH,
    remote_long_pocket_depth: float = REMOTE_LONG_POCKET_DEPTH,
    remote_long_fillet: float = REMOTE_LONG_FILLET,
    remote_short_count: int = REMOTE_SHORT_COUNT,
    remote_short_width: float = REMOTE_SHORT_WIDTH,
    remote_short_depth: float = REMOTE_SHORT_DEPTH,
    remote_short_pocket_depth: float = REMOTE_SHORT_POCKET_DEPTH,
    remote_short_fillet: float = REMOTE_SHORT_FILLET,
    remote_spacing: float = REMOTE_SPACING,
    remote_offset_x: float = REMOTE_OFFSET_X,
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    pen_positions: list = PEN_POSITIONS,
    **_kw,
) -> cq.Workplane:
    """Stage: body with remote & pen pockets cut from the top."""
    body = filleted_box(width, depth, height, fillet)
    body = _cut_remote_pockets(
        body, height,
        remote_long_count, remote_long_width, remote_long_depth,
        remote_long_pocket_depth, remote_long_fillet,
        remote_short_count, remote_short_width, remote_short_depth,
        remote_short_pocket_depth, remote_short_fillet,
        remote_spacing, remote_offset_x,
    )
    body = _cut_pen_pockets(
        body, height,
        pen_diameter, pen_pocket_depth, pen_positions,
    )
    return body


def build_full(
    width: float = BODY_WIDTH,
    depth: float = BODY_DEPTH,
    height: float = BODY_HEIGHT,
    fillet: float = BODY_FILLET,
    remote_long_count: int = REMOTE_LONG_COUNT,
    remote_long_width: float = REMOTE_LONG_WIDTH,
    remote_long_depth: float = REMOTE_LONG_DEPTH,
    remote_long_pocket_depth: float = REMOTE_LONG_POCKET_DEPTH,
    remote_long_fillet: float = REMOTE_LONG_FILLET,
    remote_short_count: int = REMOTE_SHORT_COUNT,
    remote_short_width: float = REMOTE_SHORT_WIDTH,
    remote_short_depth: float = REMOTE_SHORT_DEPTH,
    remote_short_pocket_depth: float = REMOTE_SHORT_POCKET_DEPTH,
    remote_short_fillet: float = REMOTE_SHORT_FILLET,
    remote_spacing: float = REMOTE_SPACING,
    remote_offset_x: float = REMOTE_OFFSET_X,
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    pen_positions: list = PEN_POSITIONS,
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
        remote_long_count=remote_long_count, remote_long_width=remote_long_width,
        remote_long_depth=remote_long_depth, remote_long_pocket_depth=remote_long_pocket_depth,
        remote_long_fillet=remote_long_fillet,
        remote_short_count=remote_short_count, remote_short_width=remote_short_width,
        remote_short_depth=remote_short_depth, remote_short_pocket_depth=remote_short_pocket_depth,
        remote_short_fillet=remote_short_fillet,
        remote_spacing=remote_spacing, remote_offset_x=remote_offset_x,
        pen_diameter=pen_diameter, pen_pocket_depth=pen_pocket_depth,
        pen_positions=pen_positions,
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
    body = filleted_box(width, depth, split_z, fillet)

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
    body = on_build_plate(body)

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
    remote_long_count: int = REMOTE_LONG_COUNT,
    remote_long_width: float = REMOTE_LONG_WIDTH,
    remote_long_depth: float = REMOTE_LONG_DEPTH,
    remote_long_pocket_depth: float = REMOTE_LONG_POCKET_DEPTH,
    remote_long_fillet: float = REMOTE_LONG_FILLET,
    remote_short_count: int = REMOTE_SHORT_COUNT,
    remote_short_width: float = REMOTE_SHORT_WIDTH,
    remote_short_depth: float = REMOTE_SHORT_DEPTH,
    remote_short_pocket_depth: float = REMOTE_SHORT_POCKET_DEPTH,
    remote_short_fillet: float = REMOTE_SHORT_FILLET,
    remote_spacing: float = REMOTE_SPACING,
    remote_offset_x: float = REMOTE_OFFSET_X,
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    pen_positions: list = PEN_POSITIONS,
    **_kw,
) -> cq.Workplane:
    """
    Printable top half — remote & pen pockets + alignment pin holes on
    the split face (bottom).

    Rotated 180° around the X axis so pocket openings face up and the
    split face (with pin holes) is on top.  Print in this orientation.
    """
    top_height = height - split_z
    body = filleted_box(width, depth, top_height, fillet)

    # Cut remote & pen pockets from the top (which is at Z = top_height)
    body = _cut_remote_pockets(
        body, top_height,
        remote_long_count, remote_long_width, remote_long_depth,
        remote_long_pocket_depth, remote_long_fillet,
        remote_short_count, remote_short_width, remote_short_depth,
        remote_short_pocket_depth, remote_short_fillet,
        remote_spacing, remote_offset_x,
    )
    body = _cut_pen_pockets(
        body, top_height,
        pen_diameter, pen_pocket_depth, pen_positions,
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


def build_pen_insert_short(
    pen_diameter: float = PEN_DIAMETER,
    pen_pocket_depth: float = PEN_POCKET_DEPTH,
    **_kw,
) -> cq.Workplane:
    """
    Short cylindrical insert that sits inside a pen pocket.

    - Diameter is 10% smaller than the pen pocket diameter so it drops
      in with a loose fit.
    - Height is a quarter of the pen pocket depth.
    """
    insert_diameter = pen_diameter * 0.9
    insert_height = pen_pocket_depth / 4
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
    "pen_insert_short": build_pen_insert_short,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PARAMS = {
    # Body
    "width": (BODY_WIDTH, "Overall body width (X)"),
    "depth": (BODY_DEPTH, "Overall body depth (Y)"),
    "height": (BODY_HEIGHT, "Overall body height (Z)"),
    "wall": (BODY_WALL, "Shell wall thickness"),
    "fillet": (BODY_FILLET, "Vertical edge fillet radius"),

    # Remote slots — long
    "remote_long_count": (REMOTE_LONG_COUNT, None, int),
    "remote_long_width": REMOTE_LONG_WIDTH,
    "remote_long_depth": REMOTE_LONG_DEPTH,
    "remote_long_pocket_depth": REMOTE_LONG_POCKET_DEPTH,

    # Remote slots — short
    "remote_short_count": (REMOTE_SHORT_COUNT, None, int),
    "remote_short_width": REMOTE_SHORT_WIDTH,
    "remote_short_depth": REMOTE_SHORT_DEPTH,
    "remote_short_pocket_depth": REMOTE_SHORT_POCKET_DEPTH,

    # Remote layout
    "remote_spacing": REMOTE_SPACING,

    # Pen slots
    "pen_diameter": PEN_DIAMETER,
    "pen_pocket_depth": PEN_POCKET_DEPTH,

    # Split / alignment pins
    "split_z": (SPLIT_Z, "Z height where body splits into two halves"),
    "pin_diameter": PIN_DIAMETER,
    "pin_height": PIN_HEIGHT,

    # Phone slots
    "phone_count": (PHONE_COUNT, None, int),
    "phone_width": (PHONE_WIDTH, "Width of slot opening on the side face (Y)"),
    "phone_gap_bottom": (PHONE_GAP_BOTTOM, "Height of bottom slot opening (Z)"),
    "phone_gap_top": (PHONE_GAP_TOP, "Height of top slot opening (Z)"),
    "phone_interior_length": (PHONE_INTERIOR_LENGTH,
                              "How far the phone extends into the body (X)"),
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
