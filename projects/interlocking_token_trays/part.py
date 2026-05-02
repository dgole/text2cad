#!/usr/bin/env python3
"""
Interlocking Token Trays — main part builder.

Description:
    Generates parametric rectangular tray bodies. Future stages will add
    interior dividers, interlocking features (tabs/slots), and lids.

Usage:
    python part.py block
    python part.py block --body-x 100 --body-y 60 --body-z 30
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
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

BODY_X = CFG["body_x"]
BODY_Y = CFG["body_y"]
BODY_Z = CFG["body_z"]
WALL_THICKNESS = CFG["wall_thickness"]
FLOOR_THICKNESS = CFG["floor_thickness"]
CAVITY_TAPER = CFG["cavity_taper"]
FILLET_OUTER = CFG["fillet_outer"]
FILLET_INNER = CFG["fillet_inner"]
FILLET_INNER_VERTICAL = CFG["fillet_inner_vertical"]
MAGNET_DIAMETER = CFG["magnet_diameter"]
MAGNET_HEIGHT = CFG["magnet_height"]
MAGNETS_PER_WALL = CFG["magnets_per_wall"]
MAGNET_POCKET_HEIGHT = CFG["magnet_pocket_height"]
MAGNET_SPACING = CFG["magnet_spacing"]
MAGNET_CLEARANCE = CFG["magnet_clearance"]
MAGNET_OUTER_OFFSET = CFG["magnet_outer_offset"]
KEY_DEPTH = CFG["key_depth"]
KEY_WIDTH = CFG["key_width"]
KEY_HEIGHT = CFG["key_height"]
KEY_CLEARANCE = CFG["key_clearance"]


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def block(
    body_x: float = BODY_X,
    body_y: float = BODY_Y,
    body_z: float = BODY_Z,
    wall: float = WALL_THICKNESS,
    floor: float = FLOOR_THICKNESS,
    taper: float = CAVITY_TAPER,
    fillet_outer: float = FILLET_OUTER,
    fillet_inner: float = FILLET_INNER,
    fillet_inner_vert: float = FILLET_INNER_VERTICAL,
) -> cq.Workplane:
    """Open-top rectangular tray with tapered interior walls and fillets."""
    cavity_x = body_x - 2 * wall
    cavity_y = body_y - 2 * wall
    cavity_z = body_z - floor

    # Draft angle: taper is the per-side inward offset at the floor.
    # arctan(offset / depth) gives the draft angle for cutBlind.
    taper_angle = math.degrees(math.atan(taper / cavity_z))

    result = (
        cq.Workplane("XY")
        .box(body_x, body_y, body_z)
    )

    # Round the 4 outer vertical edges (box corners)
    if fillet_outer > 0:
        result = result.edges("|Z").fillet(fillet_outer)

    # Cut tapered interior pocket from the top face.
    # If fillet_inner_vert > 0, round the 2D profile corners first
    # so the vertical cavity edges come out smooth.
    wp = result.faces(">Z").workplane()
    if fillet_inner_vert > 0:
        result = (
            wp
            .sketch()
            .rect(cavity_x, cavity_y)
            .vertices()
            .fillet(fillet_inner_vert)
            .finalize()
            .cutBlind(-cavity_z, taper=taper_angle)
        )
    else:
        result = (
            wp
            .rect(cavity_x, cavity_y)
            .cutBlind(-cavity_z, taper=taper_angle)
        )

    # Round interior bottom edges (floor-to-wall transition).
    # Select only straight edges — the curved arcs from the
    # 2D sketch fillet cannot be 3D-filleted by OCCT.
    if fillet_inner > 0:
        floor_z = -body_z / 2 + floor
        result = (
            result
            .faces(cq.NearestToPointSelector((0, 0, floor_z)))
            .edges("%Line")
            .fillet(fillet_inner)
        )

    return result




def _cut_magnet_pockets(
    result: cq.Workplane,
    body_x: float, body_y: float, body_z: float,
    floor: float,
    mag_d: float, mag_h: float, clearance: float,
    magnets_per_wall: int, pocket_height: float, mag_spacing: float,
    outer_offset: float,
) -> cq.Workplane:
    """Cut rectangular magnet pockets into all 4 walls.

    Each pocket is a rectangular prism open from the top at the pause
    layer.  The pocket starts at floor level and extends upward by
    pocket_height.  Width (along wall) fits the magnet diameter +
    clearance; depth (through wall) fits magnet height + clearance.
    Positioned so the pocket's outer face is `outer_offset` from the
    outer box surface.
    """
    # Pocket dimensions
    pocket_w = mag_d + clearance       # width along wall face
    pocket_d = mag_h + clearance       # depth through wall
    pocket_h = pocket_height           # vertical extent

    # Absolute Z coordinates (box centered at origin)
    pocket_bot_z = -body_z / 2 + floor
    pocket_top_z = pocket_bot_z + pocket_h
    pocket_mid_z = (pocket_bot_z + pocket_top_z) / 2

    # Positions along each wall (symmetric about center)
    offsets = []
    for i in range(magnets_per_wall):
        pos = (i - (magnets_per_wall - 1) / 2) * mag_spacing
        offsets.append(pos)

    # Through-wall center: outer_offset to nearest pocket face,
    # so pocket center is outer_offset + pocket_d/2 from outer surface.
    inset = outer_offset + pocket_d / 2

    # --- +X / -X walls (run along Y) ---
    for y_pos in offsets:
        for sign in (+1, -1):
            pocket_center_x = sign * (body_x / 2 - inset)
            pocket = (
                cq.Workplane("XY")
                .transformed(offset=(pocket_center_x, y_pos, pocket_mid_z))
                .box(pocket_d, pocket_w, pocket_h)
            )
            result = result.cut(pocket)

    # --- +Y / -Y walls (run along X) ---
    for x_pos in offsets:
        for sign in (+1, -1):
            pocket_center_y = sign * (body_y / 2 - inset)
            pocket = (
                cq.Workplane("XY")
                .transformed(offset=(x_pos, pocket_center_y, pocket_mid_z))
                .box(pocket_w, pocket_d, pocket_h)
            )
            result = result.cut(pocket)

    return result


def tray(**kwargs) -> cq.Workplane:
    """Tray with rectangular magnet pockets in all 4 walls.

    Print, pause at the reported Z height, drop magnets into the
    open-top slots, then resume to seal them in.
    """
    # Separate magnet kwargs from block kwargs
    mag_d = kwargs.pop("mag_d", MAGNET_DIAMETER)
    mag_h = kwargs.pop("mag_h", MAGNET_HEIGHT)
    clearance = kwargs.pop("clearance", MAGNET_CLEARANCE)
    magnets_per_wall = kwargs.pop("magnets_per_wall", MAGNETS_PER_WALL)
    pocket_height = kwargs.pop("pocket_height", MAGNET_POCKET_HEIGHT)
    mag_spacing = kwargs.pop("mag_spacing", MAGNET_SPACING)
    outer_offset = kwargs.pop("outer_offset", MAGNET_OUTER_OFFSET)

    # Read block kwargs (needed for pocket placement)
    body_x = kwargs.get("body_x", BODY_X)
    body_y = kwargs.get("body_y", BODY_Y)
    body_z = kwargs.get("body_z", BODY_Z)
    floor_v = kwargs.get("floor", FLOOR_THICKNESS)

    result = block(**kwargs)

    # Cut magnet pockets
    result = _cut_magnet_pockets(
        result, body_x, body_y, body_z, floor_v,
        mag_d, mag_h, clearance, magnets_per_wall, pocket_height, mag_spacing,
        outer_offset,
    )

    # Report pause height
    pause_z = floor_v + pocket_height
    total_magnets = 4 * magnets_per_wall
    magnet_top_z = floor_v + mag_d  # magnet sits at pocket bottom, top of disc
    headroom = pause_z - magnet_top_z
    print(f">>> PAUSE print at Z = {pause_z:.1f} mm")
    print(f">>> Drop in {total_magnets} magnets ({magnets_per_wall} per wall).")
    print(f">>> Magnet top sits {headroom:.1f} mm below the pause surface, then resume.")

    return result


def _split_at_z(body: cq.Workplane, z_abs: float):
    """Bisect a solid at an absolute Z height. Returns (bottom, top)."""
    big = 1000  # oversized cutting plane
    upper = (
        cq.Workplane("XY")
        .workplane(offset=z_abs)
        .rect(big, big)
        .extrude(big)
    )
    lower = (
        cq.Workplane("XY")
        .workplane(offset=z_abs)
        .rect(big, big)
        .extrude(-big)
    )
    bottom = body.cut(upper)
    top = body.cut(lower)
    return bottom, top


def _pause_z_abs(**kwargs) -> float:
    """Compute the absolute Z coordinate of the pause/split plane."""
    body_z = kwargs.get("body_z", BODY_Z)
    floor_v = kwargs.get("floor", FLOOR_THICKNESS)
    pocket_height = kwargs.get("pocket_height", MAGNET_POCKET_HEIGHT)
    return -body_z / 2 + floor_v + pocket_height


def tray_bottom(**kwargs) -> cq.Workplane:
    """Bottom half of the keyed tray (below pause height) — pockets and keys visible."""
    z = _pause_z_abs(**kwargs)
    full = tray_keyed(**kwargs)
    bottom, _ = _split_at_z(full, z)
    return bottom


def tray_top(**kwargs) -> cq.Workplane:
    """Top half of the keyed tray (above pause height) — the sealing cap."""
    z = _pause_z_abs(**{k: v for k, v in kwargs.items()})
    full = tray_keyed(**kwargs)
    _, top = _split_at_z(full, z)
    return top


def _add_key_features(
    result: cq.Workplane,
    body_x: float, body_y: float, body_z: float,
    key_depth: float, key_width: float, key_height: float,
    key_clearance: float,
) -> cq.Workplane:
    """Add ridge/groove polarity keying to the outer walls.

    Ridges (male) on ±X walls, grooves (female) on ±Y walls.
    Cylindrical profiles with filleted dome tops.
    Features run from the box bottom up to key_height.
    """
    bot_z = -body_z / 2
    key_mid_z = bot_z + key_height / 2
    radius = key_width / 2
    fillet_r = min(key_depth, radius) * 0.8

    # Cylinder center is inset so it protrudes exactly key_depth from the face.
    inset = radius - key_depth

    # --- Ridges on ±X walls (male / North polarity) ---
    for sign in (+1, -1):
        cx = sign * (body_x / 2 - inset)
        ridge = (
            cq.Workplane("XY")
            .transformed(offset=(cx, 0, key_mid_z))
            .cylinder(key_height, radius)
        )
        # Fillet the top circular edge for a dome
        ridge = ridge.faces(">Z").edges().fillet(fillet_r)
        result = result.union(ridge)

    # --- Grooves on ±Y walls (female / South polarity) ---
    groove_r = radius + key_clearance / 2
    groove_inset = groove_r - (key_depth + key_clearance)
    for sign in (+1, -1):
        cy = sign * (body_y / 2 - groove_inset)
        groove = (
            cq.Workplane("XY")
            .transformed(offset=(0, cy, key_mid_z))
            .cylinder(key_height, groove_r)
        )
        # Fillet the top of the groove cut too
        groove = groove.faces(">Z").edges().fillet(fillet_r)
        result = result.cut(groove)

    return result


def tray_keyed(**kwargs) -> cq.Workplane:
    """Tray with magnets and ridge/groove polarity keying.

    Ridges on ±X walls (male/North), grooves on ±Y walls (female/South).
    Ensures correct magnetic alignment when tiling trays.
    """
    key_depth = kwargs.pop("key_depth", KEY_DEPTH)
    key_width = kwargs.pop("key_width", KEY_WIDTH)
    key_height = kwargs.pop("key_height", KEY_HEIGHT)
    key_clearance = kwargs.pop("key_clearance", KEY_CLEARANCE)

    body_x = kwargs.get("body_x", BODY_X)
    body_y = kwargs.get("body_y", BODY_Y)
    body_z = kwargs.get("body_z", BODY_Z)

    result = tray(**kwargs)

    result = _add_key_features(
        result, body_x, body_y, body_z,
        key_depth, key_width, key_height, key_clearance,
    )

    return result


# ---------------------------------------------------------------------------
# Stage registry — maps CLI names to builder functions
# ---------------------------------------------------------------------------

STAGES = {
    "block": block,
    "tray": tray,
    "tray_keyed": tray_keyed,
    "tray_bottom": tray_bottom,
    "tray_top": tray_top,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("stage", choices=list(STAGES.keys()), help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--body-x", type=float, default=BODY_X, help="Body width in X (mm).")
    parser.add_argument("--body-y", type=float, default=BODY_Y, help="Body depth in Y (mm).")
    parser.add_argument("--body-z", type=float, default=BODY_Z, help="Body height in Z (mm).")
    parser.add_argument("--wall", type=float, default=WALL_THICKNESS, help="Wall thickness (mm).")
    parser.add_argument("--floor", type=float, default=FLOOR_THICKNESS, help="Floor thickness (mm).")
    parser.add_argument("--taper", type=float, default=CAVITY_TAPER, help="Per-side inward offset at cavity floor (mm).")
    parser.add_argument("--fillet-outer", type=float, default=FILLET_OUTER, help="Outer vertical edge fillet radius (mm).")
    parser.add_argument("--fillet-inner", type=float, default=FILLET_INNER, help="Inner floor edge fillet radius (mm).")
    parser.add_argument("--fillet-inner-vert", type=float, default=FILLET_INNER_VERTICAL, help="Inner vertical edge fillet radius (mm).")
    args = parser.parse_args()

    builder = STAGES[args.stage]
    body = builder(
        body_x=args.body_x, body_y=args.body_y, body_z=args.body_z,
        wall=args.wall, floor=args.floor, taper=args.taper,
        fillet_outer=args.fillet_outer, fillet_inner=args.fillet_inner,
        fillet_inner_vert=args.fillet_inner_vert,
    )
    name = f"{Path(__file__).parent.name}_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
