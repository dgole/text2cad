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

import argparse
import json
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

DOOR_THICKNESS = CFG["door_thickness"]
WALL = CFG["wall"]
LIP_HEIGHT = CFG["lip_height"]
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
    lip_height: float,
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

    # We'll build the cross section by creating a single 2D profile using
    # Workplane wire operations. Easier to just union boxes.

    # Front wall
    front_wall = (
        cq.Workplane("XZ")
        .box(wall, lip_height, 1, centered=False)
        .translate((0, 0, 0))
    )

    # Back wall
    back_wall = (
        cq.Workplane("XZ")
        .box(wall, lip_height, 1, centered=False)
        .translate((wall + gap, 0, 0))
    )

    # Bridge — connects tops of front and back walls
    bridge = (
        cq.Workplane("XZ")
        .box(total_depth, wall, 1, centered=False)
        .translate((0, lip_height - wall, 0))
    )

    # Platform — extends outward from front wall top
    platform = (
        cq.Workplane("XZ")
        .box(platform_length, platform_thickness, 1, centered=False)
        .translate((-platform_length, lip_height - platform_thickness, 0))
    )

    section = front_wall.union(back_wall).union(bridge).union(platform)
    return section


def _build_hook(
    door_thickness: float,
    wall: float,
    lip_height: float,
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
    """
    gap = door_thickness + gap_clearance
    total_depth = 2 * wall + gap

    # Build each component as a 3D box at full width, then union them.
    # All boxes start at Y=0 and extend to Y=width.
    # X=0 is the outer face of the front wall.
    # Z=0 is the bottom of the lips (lowest point).

    # Front wall: X [0, wall], Z [0, lip_height], Y [0, width]
    front_wall = (
        cq.Workplane("XY")
        .box(wall, width, lip_height, centered=False)
        .translate((0, 0, 0))
    )

    # Back wall: X [wall+gap, 2*wall+gap], Z [0, lip_height], Y [0, width]
    back_wall = (
        cq.Workplane("XY")
        .box(wall, width, lip_height, centered=False)
        .translate((wall + gap, 0, 0))
    )

    # Bridge: X [0, total_depth], Z [lip_height-wall, lip_height], Y [0, width]
    bridge = (
        cq.Workplane("XY")
        .box(total_depth, width, wall, centered=False)
        .translate((0, 0, lip_height - wall))
    )

    # Platform: extends from bottom of front wall outward
    # X [-platform_length, 0], Z [0, platform_thickness], Y [0, width]
    platform = (
        cq.Workplane("XY")
        .box(platform_length, width, platform_thickness, centered=False)
        .translate((-platform_length, 0, 0))
    )

    hook = front_wall.union(back_wall).union(bridge).union(platform)

    # Apply fillets to exposed edges where possible
    # Fillet the outer vertical edges (parallel to Y) for a nicer look
    safe_fillet = min(fillet, wall / 2 - 0.01, platform_thickness / 2 - 0.01)
    if safe_fillet > 0.2:
        try:
            hook = hook.edges("|Y").fillet(safe_fillet)
        except Exception:
            pass  # Some edge combinations may fail — skip gracefully

    return hook


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def _move_to_build_plate(body: cq.Workplane) -> cq.Workplane:
    """Translate body so its bounding box sits on Z=0."""
    bb = body.val().BoundingBox()
    if abs(bb.zmin) > 0.001:
        body = body.translate((0, 0, -bb.zmin))
    return body


def build_profile(
    door_thickness: float = DOOR_THICKNESS,
    wall: float = WALL,
    lip_height: float = LIP_HEIGHT,
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
        lip_height=lip_height,
        width=test_width,
        platform_length=platform_length,
        platform_thickness=platform_thickness,
        gap_clearance=gap_clearance,
        fillet=fillet,
    )
    # Rotate 90° around X axis to lay the cross-section flat
    hook = hook.rotateAboutCenter((1, 0, 0), -90)
    hook = _move_to_build_plate(hook)
    return hook


def build_full(
    door_thickness: float = DOOR_THICKNESS,
    wall: float = WALL,
    lip_height: float = LIP_HEIGHT,
    width: float = WIDTH,
    platform_length: float = PLATFORM_LENGTH,
    platform_thickness: float = PLATFORM_THICKNESS,
    gap_clearance: float = GAP_CLEARANCE,
    fillet: float = FILLET,
    **_kw,
) -> cq.Workplane:
    """
    Stage: full-width hook — the final part.
    """
    return _build_hook(
        door_thickness=door_thickness,
        wall=wall,
        lip_height=lip_height,
        width=width,
        platform_length=platform_length,
        platform_thickness=platform_thickness,
        gap_clearance=gap_clearance,
        fillet=fillet,
    )


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

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("stage", choices=list(STAGES.keys()),
                        help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))

    # Overrides
    parser.add_argument("--door-thickness", type=float, default=DOOR_THICKNESS)
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--lip-height", type=float, default=LIP_HEIGHT)
    parser.add_argument("--width", type=float, default=WIDTH)
    parser.add_argument("--platform-length", type=float, default=PLATFORM_LENGTH)
    parser.add_argument("--platform-thickness", type=float, default=PLATFORM_THICKNESS)
    parser.add_argument("--gap-clearance", type=float, default=GAP_CLEARANCE)
    parser.add_argument("--fillet", type=float, default=FILLET)

    args = parser.parse_args()

    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}

    body = STAGES[args.stage](**kw)

    name = f"door_hook_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
