#!/usr/bin/env python3
"""
Utility Cart Sidecar — clip-on organizer caddy

Description:
    A rectangular caddy that clips onto the thin edge of a utility cart.
    Pockets are cut from the top (all with a solid floor):
      - 2 pen holes (15 mm dia) on the left
      - 2 small remote slots (10×30 mm) in the middle
      - 2 big remote slots (20×50 mm) on the right
    A hook on the back edge wraps over the cart wall to hold the caddy
    in place.

Usage:
    python part.py clip_test   # Thin body slice + hook — verify clip fit
    python part.py body        # Full solid block + hook — check size
    python part.py full        # Complete part with all pockets
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import filleted_box, safe_fillet_radius  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

# Body
BODY_WIDTH = CFG["body_width"]
BODY_LENGTH = CFG["body_length"]
BODY_HEIGHT = CFG["body_height"]
FLOOR_THICKNESS = CFG["floor_thickness"]
WALL_THICKNESS = CFG["wall_thickness"]
FILLET_RADIUS = CFG["fillet_radius"]

# Big remote slots
BIG_REMOTE_WIDTH = CFG["big_remote_width"]
BIG_REMOTE_LENGTH = CFG["big_remote_length"]
BIG_REMOTE_COUNT = CFG["big_remote_count"]

# Small remote slots
SMALL_REMOTE_WIDTH = CFG["small_remote_width"]
SMALL_REMOTE_LENGTH = CFG["small_remote_length"]
SMALL_REMOTE_COUNT = CFG["small_remote_count"]

# Pen holes
PEN_DIAMETER = CFG["pen_diameter"]
PEN_COUNT = CFG["pen_count"]

# Hook / clip
HOOK_GAP = CFG["hook_gap"]
HOOK_LIP_HEIGHT = CFG["hook_lip_height"]
HOOK_THICKNESS = CFG["hook_thickness"]
HOOK_LENGTH = CFG["hook_length"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_hook(width: float, height: float,
               hook_length: float,
               hook_gap: float, lip_height: float,
               hook_thickness: float) -> cq.Workplane:
    """Build the clip hook that wraps over the cart wall.

    The hook is an inverted-U bracket attached to the back edge (+X side)
    of the body.  It extends outward in +X over the cart wall, then drops
    down on the far side.  It spans hook_length along Y, centered.

    Cross-section (looking along Y / length axis):

        body top ──────┬────────────────┐
                       │  bridge        │  hook_thickness (Z)
                       ├────────────────┤
                       │   gap          │  hook_gap (cart wall sits here)
                       ├────────────────┤
                       │  back lip      │  hook_thickness (X)
                       │                │
                       │  lip_height    │
                       │                │
                       └────────────────┘
    """
    # Bridge — horizontal piece on top, connects body to back lip
    bridge_extent_x = hook_thickness + hook_gap + hook_thickness
    bridge = (
        cq.Workplane("XY")
        .box(bridge_extent_x, hook_length, hook_thickness,
             centered=(True, True, False))
        .translate((width / 2 + bridge_extent_x / 2, 0,
                    height - hook_thickness))
    )

    # Back lip — vertical piece hanging down on the far side of the cart wall
    # Clamp so the lip never extends below Z=0 (body base)
    actual_lip_height = min(lip_height, height - hook_thickness)
    lip = (
        cq.Workplane("XY")
        .box(hook_thickness, hook_length, actual_lip_height,
             centered=(True, True, False))
        .translate((width / 2 + hook_thickness + hook_gap + hook_thickness / 2,
                    0,
                    height - hook_thickness - actual_lip_height))
    )

    return bridge.union(lip)


def _compute_pocket_positions(
    body_length: float,
    body_width: float,
    wall: float,
    pen_count: int, pen_diameter: float,
    small_count: int, small_length: float, small_width: float,
    big_count: int, big_length: float,
) -> list:
    """Compute (x, y) center positions for all pockets.

    All slots in a single row along +Y at X=0.
    Order along +Y: big remotes, small remotes, pen holes.

    Returns list of (type, x_center, y_center) tuples.
    """
    # (type, span_along_Y)
    specs = []
    for _ in range(big_count):
        specs.append(("big", big_length))
    for _ in range(small_count):
        specs.append(("small", small_length))
    for _ in range(pen_count):
        specs.append(("pen", pen_diameter))

    # Total span
    total_span = (
        wall
        + sum(s[1] for s in specs)
        + wall * (len(specs) - 1)
        + wall
    )

    cursor_y = -total_span / 2 + wall

    positions = []
    for (slot_type, span) in specs:
        center_y = cursor_y + span / 2
        positions.append((slot_type, 0, center_y))
        cursor_y += span + wall

    return positions


def _cut_pockets(
    body: cq.Workplane,
    height: float,
    floor_thickness: float,
    body_width: float,
    pocket_positions: list,
    pen_diameter: float,
    small_width: float, small_length: float,
    big_width: float, big_length: float,
    fillet: float,
) -> cq.Workplane:
    """Cut all pockets from the top face of the body."""
    pocket_depth = height - floor_thickness

    for (slot_type, x_center, y_center) in pocket_positions:
        if slot_type == "pen":
            pocket = (
                cq.Workplane("XY")
                .workplane(offset=height)
                .center(x_center, y_center)
                .circle(pen_diameter / 2)
                .extrude(-pocket_depth)
            )
        elif slot_type == "small":
            # width spans X (body depth), length spans Y (body length)
            rx, ry = small_width, small_length
            safe_f = safe_fillet_radius(fillet, rx, ry)
            pocket = (
                cq.Workplane("XY")
                .workplane(offset=height)
                .center(x_center, y_center)
                .rect(rx, ry)
                .extrude(-pocket_depth)
            )
            if safe_f > 0.01:
                pocket = pocket.edges("|Z").fillet(safe_f)
        else:  # big
            # width spans X (body depth), length spans Y (body length)
            rx, ry = big_width, big_length
            safe_f = safe_fillet_radius(fillet, rx, ry)
            pocket = (
                cq.Workplane("XY")
                .workplane(offset=height)
                .center(x_center, y_center)
                .rect(rx, ry)
                .extrude(-pocket_depth)
            )
            if safe_f > 0.01:
                pocket = pocket.edges("|Z").fillet(safe_f)

        body = body.cut(pocket)

    return body


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def build_clip_test(
    width: float = BODY_WIDTH,
    length: float = BODY_LENGTH,
    height: float = BODY_HEIGHT,
    fillet: float = FILLET_RADIUS,
    hook_gap: float = HOOK_GAP,
    lip_height: float = HOOK_LIP_HEIGHT,
    hook_thickness: float = HOOK_THICKNESS,
    hook_length: float = HOOK_LENGTH,
    **_kw,
) -> cq.Workplane:
    """Stage: thin body slice (20mm tall) + full hook — test clip fit."""
    test_height = 20
    body = filleted_box(width, length, test_height, fillet)
    hook = _make_hook(width, test_height, hook_length, hook_gap, lip_height,
                      hook_thickness)
    return body.union(hook)


def build_body(
    width: float = BODY_WIDTH,
    length: float = BODY_LENGTH,
    height: float = BODY_HEIGHT,
    fillet: float = FILLET_RADIUS,
    hook_gap: float = HOOK_GAP,
    lip_height: float = HOOK_LIP_HEIGHT,
    hook_thickness: float = HOOK_THICKNESS,
    hook_length: float = HOOK_LENGTH,
    **_kw,
) -> cq.Workplane:
    """Stage: full solid block + hook — check overall size."""
    body = filleted_box(width, length, height, fillet)
    hook = _make_hook(width, height, hook_length, hook_gap, lip_height,
                      hook_thickness)
    return body.union(hook)


def build_full(
    width: float = BODY_WIDTH,
    length: float = BODY_LENGTH,
    height: float = BODY_HEIGHT,
    fillet: float = FILLET_RADIUS,
    floor_thickness: float = FLOOR_THICKNESS,
    wall: float = WALL_THICKNESS,
    big_width: float = BIG_REMOTE_WIDTH,
    big_length: float = BIG_REMOTE_LENGTH,
    big_count: int = BIG_REMOTE_COUNT,
    small_width: float = SMALL_REMOTE_WIDTH,
    small_length: float = SMALL_REMOTE_LENGTH,
    small_count: int = SMALL_REMOTE_COUNT,
    pen_diameter: float = PEN_DIAMETER,
    pen_count: int = PEN_COUNT,
    hook_gap: float = HOOK_GAP,
    lip_height: float = HOOK_LIP_HEIGHT,
    hook_thickness: float = HOOK_THICKNESS,
    hook_length: float = HOOK_LENGTH,
    **_kw,
) -> cq.Workplane:
    """Stage: complete part with all pockets + hook."""
    body = filleted_box(width, length, height, fillet)
    hook = _make_hook(width, height, hook_length, hook_gap, lip_height,
                      hook_thickness)
    body = body.union(hook)

    positions = _compute_pocket_positions(
        length, width, wall,
        pen_count, pen_diameter,
        small_count, small_length, small_width,
        big_count, big_length,
    )

    body = _cut_pockets(
        body, height, floor_thickness, width, positions,
        pen_diameter,
        small_width, small_length,
        big_width, big_length,
        fillet,
    )

    return body


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "clip_test": build_clip_test,
    "body": build_body,
    "full": build_full,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PARAMS = {
    # Body
    "width": BODY_WIDTH,
    "length": BODY_LENGTH,
    "height": BODY_HEIGHT,
    "fillet": FILLET_RADIUS,
    "floor_thickness": FLOOR_THICKNESS,
    "wall": WALL_THICKNESS,

    # Remote slots
    "big_width": BIG_REMOTE_WIDTH,
    "big_length": BIG_REMOTE_LENGTH,
    "big_count": (BIG_REMOTE_COUNT, None, int),
    "small_width": SMALL_REMOTE_WIDTH,
    "small_length": SMALL_REMOTE_LENGTH,
    "small_count": (SMALL_REMOTE_COUNT, None, int),

    # Pens
    "pen_diameter": PEN_DIAMETER,
    "pen_count": (PEN_COUNT, None, int),

    # Hook
    "hook_gap": HOOK_GAP,
    "lip_height": HOOK_LIP_HEIGHT,
    "hook_thickness": HOOK_THICKNESS,
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
