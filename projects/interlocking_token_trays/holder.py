#!/usr/bin/env python3
"""
Interlocking Token Trays — stack holder.

Generates a simple rectangular holder that stores a vertical stack of
8 token trays.  The interior is sized to clear the keying features
(ridges on ±X, grooves on ±Y) with a small tolerance.

Usage:
    python holder.py shell
    python holder.py holder
    python holder.py holder --num-trays 6
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

BODY_X = CFG["body_x"]            # tray outer width
BODY_Y = CFG["body_y"]            # tray outer depth
BODY_Z = CFG["body_z"]            # tray outer height (single tray)
KEY_DEPTH = CFG["key_depth"]      # ridge protrusion beyond wall
FILLET_OUTER = CFG["fillet_outer"]

# ---------------------------------------------------------------------------
# Holder-specific defaults (will be added to config.json)
# ---------------------------------------------------------------------------

HOLDER_NUM_TRAYS = CFG.get("holder_num_trays", 8)
HOLDER_WALL = CFG.get("holder_wall", 2.5)
HOLDER_FLOOR = CFG.get("holder_floor", 2.0)
HOLDER_FIT_CLEARANCE = CFG.get("holder_fit_clearance", 0.5)
HOLDER_FILLET = CFG.get("holder_fillet", 3.0)
HOLDER_RELIEF_WIDTH = CFG.get("holder_relief_width", 40.0)
HOLDER_RELIEF_BASE = CFG.get("holder_relief_base", 20.0)
HOLDER_RELIEF_DEPTH = CFG.get("holder_relief_depth", 15.0)
HOLDER_RELIEF_FILLET = CFG.get("holder_relief_fillet", 5.0)


# ---------------------------------------------------------------------------
# Derived dimensions
# ---------------------------------------------------------------------------

def _dims(
    body_x: float = BODY_X,
    body_y: float = BODY_Y,
    body_z: float = BODY_Z,
    key_depth: float = KEY_DEPTH,
    num_trays: int = HOLDER_NUM_TRAYS,
    wall: float = HOLDER_WALL,
    floor: float = HOLDER_FLOOR,
    clearance: float = HOLDER_FIT_CLEARANCE,
):
    """Compute holder envelope dimensions."""
    # Interior must clear the tray footprint plus keying protrusions.
    # Ridges protrude key_depth on ±X walls, so interior X needs
    # body_x + 2*key_depth + clearance on each side.
    interior_x = body_x + 2 * key_depth + 2 * clearance
    interior_y = body_y + 2 * key_depth + 2 * clearance
    interior_z = body_z * num_trays

    outer_x = interior_x + 2 * wall
    outer_y = interior_y + 2 * wall
    # Open top, so outer height = floor + stack height
    outer_z = floor + interior_z

    return {
        "interior_x": interior_x,
        "interior_y": interior_y,
        "interior_z": interior_z,
        "outer_x": outer_x,
        "outer_y": outer_y,
        "outer_z": outer_z,
        "floor": floor,
        "wall": wall,
    }


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def shell(
    body_x: float = BODY_X,
    body_y: float = BODY_Y,
    body_z: float = BODY_Z,
    key_depth: float = KEY_DEPTH,
    num_trays: int = HOLDER_NUM_TRAYS,
    wall: float = HOLDER_WALL,
    floor: float = HOLDER_FLOOR,
    clearance: float = HOLDER_FIT_CLEARANCE,
    fillet: float = HOLDER_FILLET,
    **_kwargs,
) -> cq.Workplane:
    """Open-top rectangular shell — the basic holder box."""
    d = _dims(body_x, body_y, body_z, key_depth, num_trays, wall, floor, clearance)

    # Build solid block, centered at XY origin, bottom face on Z=0
    result = (
        cq.Workplane("XY")
        .box(d["outer_x"], d["outer_y"], d["outer_z"], centered=(True, True, False))
    )

    # Fillet outer vertical edges
    safe_fillet = min(fillet, d["wall"] - 0.1)
    if safe_fillet > 0:
        result = result.edges("|Z").fillet(safe_fillet)

    # Cut interior cavity from the top
    result = (
        result
        .faces(">Z")
        .workplane()
        .rect(d["interior_x"], d["interior_y"])
        .cutBlind(-d["interior_z"])
    )

    return result


def holder(
    body_x: float = BODY_X,
    body_y: float = BODY_Y,
    body_z: float = BODY_Z,
    key_depth: float = KEY_DEPTH,
    num_trays: int = HOLDER_NUM_TRAYS,
    wall: float = HOLDER_WALL,
    floor: float = HOLDER_FLOOR,
    clearance: float = HOLDER_FIT_CLEARANCE,
    fillet: float = HOLDER_FILLET,
    relief_width: float = HOLDER_RELIEF_WIDTH,
    relief_base: float = HOLDER_RELIEF_BASE,
    relief_depth: float = HOLDER_RELIEF_DEPTH,
    relief_fillet: float = HOLDER_RELIEF_FILLET,
    **_kwargs,
) -> cq.Workplane:
    """Full holder — shell with finger-relief cutouts on two opposite walls.

    The relief cutouts are centered on the ±Y walls so you can reach in
    and grab any tray in the stack.  `relief_base` controls how much wall
    remains above the floor.
    """
    d = _dims(body_x, body_y, body_z, key_depth, num_trays, wall, floor, clearance)
    result = shell(
        body_x, body_y, body_z, key_depth, num_trays,
        wall, floor, clearance, fillet,
    )

    # Finger-relief: cutout on ±Y walls from the top down, leaving
    # relief_base mm of wall above the floor.
    relief_height = d["outer_z"] - d["floor"] - relief_base
    safe_relief_w = min(relief_width, d["interior_x"] - 4.0)
    safe_relief_h = max(0.0, min(relief_height, d["outer_z"] - d["floor"] - 2.0))

    if safe_relief_w > 0 and safe_relief_h > 0:
        # Cut with a plain box that extends above the top for a clean
        # open edge — no rounding at the top.
        overshoot = 10.0  # extend above holder top
        box_h = safe_relief_h + overshoot
        for sign in (+1, -1):
            cy = sign * d["outer_y"] / 2
            cz = d["outer_z"] + overshoot / 2 - box_h / 2
            cutout = (
                cq.Workplane("XY")
                .transformed(offset=(0, cy, cz))
                .box(safe_relief_w, relief_depth, box_h)
            )
            result = result.cut(cutout)

        # Fillet the vertical edges at the cutout boundaries.
        # These are the edges where the cutout side faces meet the
        # outer and inner wall surfaces — 4 edges per cutout, per face.
        # Outer edges get the full radius; inner edges get a smaller
        # radius so they don't conflict with the outer fillet.
        outer_rf = min(relief_fillet, d["wall"] - 0.1)
        inner_rf = min(relief_fillet, d["wall"] / 2 - 0.1)
        mid_z = d["floor"] + relief_base + safe_relief_h / 2

        for rf, y_func in (
            (outer_rf, lambda sy: sy * d["outer_y"] / 2),
            (inner_rf, lambda sy: sy * d["interior_y"] / 2),
        ):
            if rf <= 0:
                continue
            for sign_y in (+1, -1):
                for sign_x in (+1, -1):
                    pt = (
                        sign_x * safe_relief_w / 2,
                        y_func(sign_y),
                        mid_z,
                    )
                    try:
                        result = (
                            result
                            .edges(cq.NearestToPointSelector(pt))
                            .fillet(rf)
                        )
                    except Exception:
                        pass

    # Print summary
    print(f"Holder: {d['outer_x']:.1f} x {d['outer_y']:.1f} x {d['outer_z']:.1f} mm")
    print(f"Interior: {d['interior_x']:.1f} x {d['interior_y']:.1f} x {d['interior_z']:.1f} mm")
    print(f"Fits {num_trays} trays ({body_z:.0f} mm each = {d['interior_z']:.0f} mm stack)")

    return result


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "shell": shell,
    "holder": holder,
}

# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PARAMS = {
    "num_trays": (HOLDER_NUM_TRAYS, "Number of trays in the stack.", int),
    "wall": (HOLDER_WALL, "Holder wall thickness (mm)."),
    "floor": (HOLDER_FLOOR, "Holder floor thickness (mm)."),
    "clearance": (HOLDER_FIT_CLEARANCE, "Fit clearance around trays (mm)."),
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
