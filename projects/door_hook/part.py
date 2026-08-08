#!/usr/bin/env python3
"""
Door Hook — over-the-door hook with projector platform.

Description:
    A clip that fits over the top of a door with a flat platform extending
    outward to hold a small portable projector. The cross-section is a
    U-channel (front wall + bridge + back wall) with a horizontal shelf
    extending from the top of the front wall.

    Side-view cross-section:

              bridge (sits on door top)
         ┌──────────────────────────────────┐
         │                                  │
         │  front wall          back wall   │
         │                                  │
         │                                  │
         │                                  │
    ┌────┘                                  └───┐
    │  platform                                 │
    └───────────┘

    The platform extends from the bottom of the front wall into the room.
    The U-channel opens downward to clip over the door.

Usage:
    python part.py profile     # Thin cross-section slice — check fit on door
    python part.py full        # Complete hook at full width
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import on_build_plate, safe_fillet_radius  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

DOOR_THICKNESS = CFG["door_thickness"]
WALL = CFG["wall"]
FRONT_LIP_HEIGHT = CFG["front_lip_height"]
FRONT_LIP_EXTENSION = CFG["front_lip_extension"]
BACK_LIP_HEIGHT = CFG["back_lip_height"]
WIDTH = CFG["width"]
PLATFORM_LENGTH = CFG["platform_length"]
PLATFORM_THICKNESS = CFG["platform_thickness"]
GAP_CLEARANCE = CFG["gap_clearance"]
FILLET = CFG["fillet"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_cross_section(
    door_thickness: float,
    wall: float,
    front_lip_height: float,
    back_lip_height: float,
    platform_length: float,
    platform_thickness: float,
    gap_clearance: float,
) -> cq.Sketch:
    """
    Build the 2D cross-section of the hook as a CQ Wire on the XZ plane.

    Coordinate system (looking at cross-section from the side):
      - X = horizontal (depth direction: front-of-door to back-of-door)
      - Z = vertical (up/down)

    We build this as a series of rectangles unioned / positioned.

    Layout (Z=0 is the bottom of the bridge, which sits on top of the door):

        Platform top: Z = lip_height + platform_thickness
        Platform bottom / top of front wall: Z = lip_height
        Bridge top / Z=0 is at the TOP of the door
        Bridge bottom = front/back wall tops... wait, let me re-think.

    Actually let's lay it out so Z=0 is at the bottom of the back wall
    (the lowest point), making the whole thing sit on the build plate.

    From bottom to top:
      - Back wall: from Z=0 to Z=lip_height, width=wall
      - Front wall: from Z=0 to Z=lip_height, width=wall
      - Bridge: connects front and back walls at the top, at Z=(lip_height - wall) to Z=lip_height
        Actually no — the bridge is at the TOP of the lips. The U-channel
        opening faces downward (to slide onto the door from above).

    Let me think about this differently. The shape from the side:

      The U-channel opens DOWNWARD to clip over the door top.
      - Bridge is at the top.
      - Front and back walls hang down from the bridge.
      - Platform extends outward from the top of the front wall (= bridge level).

    So with Z=0 at the bottom of the walls (lowest point):

      Back wall:  X from (wall + gap) to (2*wall + gap),  Z from 0 to lip_height
      Front wall: X from 0 to wall,                       Z from 0 to lip_height
      Bridge:     X from 0 to (2*wall + gap),             Z from (lip_height - wall) to lip_height
      Platform:   X from (-platform_length) to 0,         Z from (lip_height - platform_thickness) to lip_height

    Where gap = door_thickness + gap_clearance
    """
    gap = door_thickness + gap_clearance
    total_depth = 2 * wall + gap  # front wall + gap + back wall
    bridge_z = max(front_lip_height, back_lip_height)  # bridge sits at the tallest lip

    # We'll build the cross section by creating a single 2D profile using
    # Workplane wire operations. Easier to just union boxes.

    # Front wall — bottom at (bridge_z - front_lip_height), top at bridge_z
    front_wall = (
        cq.Workplane("XZ")
        .box(wall, front_lip_height, 1, centered=False)
        .translate((0, bridge_z - front_lip_height, 0))
    )

    # Back wall — bottom at (bridge_z - back_lip_height), top at bridge_z
    back_wall = (
        cq.Workplane("XZ")
        .box(wall, back_lip_height, 1, centered=False)
        .translate((wall + gap, bridge_z - back_lip_height, 0))
    )

    # Bridge — connects tops of front and back walls at the highest point
    bridge = (
        cq.Workplane("XZ")
        .box(total_depth, wall, 1, centered=False)
        .translate((0, bridge_z - wall, 0))
    )

    # Platform — extends outward from front wall top (at bridge level)
    platform = (
        cq.Workplane("XZ")
        .box(platform_length, platform_thickness, 1, centered=False)
        .translate((-platform_length, bridge_z - platform_thickness, 0))
    )

    section = front_wall.union(back_wall).union(bridge).union(platform)
    return section


def _build_hook(
    door_thickness: float,
    wall: float,
    front_lip_height: float,
    front_lip_extension: float,
    back_lip_height: float,
    width: float,
    platform_length: float,
    platform_thickness: float,
    gap_clearance: float,
    fillet: float,
) -> cq.Workplane:
    """
    Build the full 3D hook by constructing the cross-section profile
    and extruding it along the width (Y axis).

    We build with box primitives and boolean union, then extrude to width.

    The front wall has two sections:
      1. From the bridge down to the platform attachment (front_lip_height).
      2. Below the platform, continuing down by front_lip_extension.
    """
    gap = door_thickness + gap_clearance
    total_depth = 2 * wall + gap
    bridge_z = max(front_lip_height, back_lip_height)  # bridge at tallest lip

    # Build each component as a 3D box at full width, then union them.
    # All boxes start at Y=0 and extend to Y=width.
    # X=0 is the outer face of the front wall.
    # Z=0 is the bottom of the front wall (where platform meets front wall).
    # Negative Z = below the platform.

    # Front wall: bottom at Z=(bridge_z - front_lip_height), top at Z=bridge_z
    front_wall = (
        cq.Workplane("XY")
        .box(wall, width, front_lip_height, centered=False)
        .translate((0, 0, bridge_z - front_lip_height))
    )

    # Front lip extension: continues below the platform attachment point
    if front_lip_extension > 0:
        front_ext = (
            cq.Workplane("XY")
            .box(wall, width, front_lip_extension, centered=False)
            .translate((0, 0, -front_lip_extension))
        )
        front_wall = front_wall.union(front_ext)

    # Back wall: bottom at Z=(bridge_z - back_lip_height), top at Z=bridge_z
    back_wall = (
        cq.Workplane("XY")
        .box(wall, width, back_lip_height, centered=False)
        .translate((wall + gap, 0, bridge_z - back_lip_height))
    )

    # Bridge: X [0, total_depth], Z [bridge_z-wall, bridge_z], Y [0, width]
    bridge = (
        cq.Workplane("XY")
        .box(total_depth, width, wall, centered=False)
        .translate((0, 0, bridge_z - wall))
    )

    # Platform: extends from front wall at the bottom of the front lip
    # X [-platform_length, 0], Z [0, platform_thickness], Y [0, width]
    platform = (
        cq.Workplane("XY")
        .box(platform_length, width, platform_thickness, centered=False)
        .translate((-platform_length, 0, 0))
    )

    hook = front_wall.union(back_wall).union(bridge).union(platform)

    # Apply fillets to exposed edges where possible
    # Fillet the outer vertical edges (parallel to Y) for a nicer look
    safe_fillet = safe_fillet_radius(fillet, wall, platform_thickness)
    if safe_fillet > 0.2:
        try:
            hook = hook.edges("|Y").fillet(safe_fillet)
        except Exception:
            pass  # Some edge combinations may fail — skip gracefully

    return hook


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def build_profile(
    door_thickness: float = DOOR_THICKNESS,
    wall: float = WALL,
    front_lip_height: float = FRONT_LIP_HEIGHT,
    front_lip_extension: float = FRONT_LIP_EXTENSION,
    back_lip_height: float = BACK_LIP_HEIGHT,
    platform_length: float = PLATFORM_LENGTH,
    platform_thickness: float = PLATFORM_THICKNESS,
    gap_clearance: float = GAP_CLEARANCE,
    fillet: float = FILLET,
    **_kw,
) -> cq.Workplane:
    """
    Stage: thin cross-section slice (2mm wide).
    Print this first to check that it fits over your door.
    Rotated 90° to lay flat on the build plate for printing.
    """
    test_width = 2.0  # thin test piece
    hook = _build_hook(
        door_thickness=door_thickness,
        wall=wall,
        front_lip_height=front_lip_height,
        front_lip_extension=front_lip_extension,
        back_lip_height=back_lip_height,
        width=test_width,
        platform_length=platform_length,
        platform_thickness=platform_thickness,
        gap_clearance=gap_clearance,
        fillet=fillet,
    )
    # Rotate 90° around X axis to lay the cross-section flat
    hook = hook.rotateAboutCenter((1, 0, 0), -90)
    hook = on_build_plate(hook)
    return hook


def build_full(
    door_thickness: float = DOOR_THICKNESS,
    wall: float = WALL,
    front_lip_height: float = FRONT_LIP_HEIGHT,
    front_lip_extension: float = FRONT_LIP_EXTENSION,
    back_lip_height: float = BACK_LIP_HEIGHT,
    width: float = WIDTH,
    platform_length: float = PLATFORM_LENGTH,
    platform_thickness: float = PLATFORM_THICKNESS,
    gap_clearance: float = GAP_CLEARANCE,
    fillet: float = FILLET,
    **_kw,
) -> cq.Workplane:
    """
    Stage: full-width hook — the final part.
    Rotated 90° so the cross-section lies flat on the build plate
    and the width extrudes upward (same orientation as profile stage).
    """
    hook = _build_hook(
        door_thickness=door_thickness,
        wall=wall,
        front_lip_height=front_lip_height,
        front_lip_extension=front_lip_extension,
        back_lip_height=back_lip_height,
        width=width,
        platform_length=platform_length,
        platform_thickness=platform_thickness,
        gap_clearance=gap_clearance,
        fillet=fillet,
    )
    hook = hook.rotateAboutCenter((1, 0, 0), -90)
    hook = on_build_plate(hook)
    return hook


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "profile": build_profile,
    "full": build_full,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

PARAMS = {
    "door_thickness": DOOR_THICKNESS,
    "wall": WALL,
    "front_lip_height": FRONT_LIP_HEIGHT,
    "front_lip_extension": FRONT_LIP_EXTENSION,
    "back_lip_height": BACK_LIP_HEIGHT,
    "width": WIDTH,
    "platform_length": PLATFORM_LENGTH,
    "platform_thickness": PLATFORM_THICKNESS,
    "gap_clearance": GAP_CLEARANCE,
    "fillet": FILLET,
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
