#!/usr/bin/env python3
"""
Part: Dust Port Adapter

A clip-on adapter for a circular saw dust exhaust port.
  - Collar clips onto the rectangular port rim
  - Arm extends to a screw hole on the saw body for anchoring
  - 90-degree elbow connects to a dust collection hose

Build stages (print and test in order):
  plate    — flat frame matching port outline (fit check)
  collar   — frame + clip lip (snap-on fit check)
  mounting — collar + screw arm (mounting alignment check)

Usage:
    python part.py plate
    python part.py collar
    python part.py plate --port-width 45 --port-height 30
"""

from __future__ import annotations

import argparse
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402
from cad.ops import add_screw_hole  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters — all dimensions in mm.  Tweak these after test prints.
# ---------------------------------------------------------------------------

# Dust port opening (inner rectangle the adapter mates to)
PORT_WIDTH = 42.0
PORT_HEIGHT = 28.0
PORT_CORNER_RADIUS = 3.0

# Rim / lip that the clip grabs onto
RIM_THICKNESS = 2.0      # how far the rim protrudes from the port face
RIM_DEPTH = 3.0          # axial depth of the rim

# Adapter body
WALL = 2.5

# Test plate
PLATE_THICKNESS = 3.0

# Screw hole
SCREW_HOLE_DIA = 4.5     # clearance for M4 / #8
SCREW_OFFSET_X = 0.0     # lateral offset from port center
SCREW_OFFSET_Y = 30.0    # distance above port center

# Hose connection (for full adapter — future)
HOSE_INNER_DIA = 35.0
HOSE_LENGTH = 25.0


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def test_plate(
    port_width: float = PORT_WIDTH,
    port_height: float = PORT_HEIGHT,
    corner_radius: float = PORT_CORNER_RADIUS,
    wall: float = WALL,
    thickness: float = PLATE_THICKNESS,
) -> cq.Workplane:
    """
    Flat frame matching the outer adapter profile with the port opening cut out.
    Print this, hold it against the port, verify the outline.
    """
    outer_w = port_width + 2 * wall
    outer_h = port_height + 2 * wall
    outer_r = corner_radius + wall if corner_radius > 0 else 0

    plate = cq.Workplane("XY").rect(outer_w, outer_h)
    plate = plate.extrude(thickness)
    if outer_r > 0:
        plate = plate.edges("|Z").fillet(min(outer_r, min(outer_w, outer_h) / 2 - 0.01))

    cutout = cq.Workplane("XY").rect(port_width, port_height)
    cutout = cutout.extrude(thickness)
    if corner_radius > 0:
        cutout = cutout.edges("|Z").fillet(min(corner_radius, min(port_width, port_height) / 2 - 0.01))

    return plate.cut(cutout)


def test_collar(
    port_width: float = PORT_WIDTH,
    port_height: float = PORT_HEIGHT,
    corner_radius: float = PORT_CORNER_RADIUS,
    wall: float = WALL,
    plate_thickness: float = PLATE_THICKNESS,
    rim_thickness: float = RIM_THICKNESS,
    rim_depth: float = RIM_DEPTH,
) -> cq.Workplane:
    """
    Frame + inward lip extending behind the plate to clip over the port rim.
    """
    plate = test_plate(port_width, port_height, corner_radius, wall, plate_thickness)

    lip_outer_w = port_width + 2 * rim_thickness
    lip_outer_h = port_height + 2 * rim_thickness
    lip_r_outer = (corner_radius + rim_thickness) if corner_radius > 0 else 0

    lip_outer = cq.Workplane("XY").rect(lip_outer_w, lip_outer_h).extrude(-rim_depth)
    if lip_r_outer > 0:
        lip_outer = lip_outer.edges("|Z").fillet(
            min(lip_r_outer, min(lip_outer_w, lip_outer_h) / 2 - 0.01)
        )

    lip_inner = cq.Workplane("XY").rect(port_width, port_height).extrude(-rim_depth)
    if corner_radius > 0:
        lip_inner = lip_inner.edges("|Z").fillet(
            min(corner_radius, min(port_width, port_height) / 2 - 0.01)
        )

    lip = lip_outer.cut(lip_inner)
    return plate.union(lip)


def test_mounting(
    port_width: float = PORT_WIDTH,
    port_height: float = PORT_HEIGHT,
    corner_radius: float = PORT_CORNER_RADIUS,
    wall: float = WALL,
    plate_thickness: float = PLATE_THICKNESS,
    rim_thickness: float = RIM_THICKNESS,
    rim_depth: float = RIM_DEPTH,
    screw_dia: float = SCREW_HOLE_DIA,
    screw_x: float = SCREW_OFFSET_X,
    screw_y: float = SCREW_OFFSET_Y,
) -> cq.Workplane:
    """
    Collar + arm extending to the screw hole.
    """
    collar = test_collar(
        port_width, port_height, corner_radius, wall,
        plate_thickness, rim_thickness, rim_depth,
    )

    outer_h = port_height + 2 * wall
    arm_width = screw_dia + 2 * wall
    arm_length = screw_y - outer_h / 2 + arm_width / 2

    if arm_length > 0:
        arm = (
            cq.Workplane("XY")
            .center(screw_x, outer_h / 2 + arm_length / 2)
            .rect(arm_width, arm_length)
            .extrude(plate_thickness)
        )
        collar = collar.union(arm)

    collar = add_screw_hole(collar, screw_dia, (screw_x, screw_y))
    return collar


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "plate": test_plate,
    "collar": test_collar,
    "mounting": test_mounting,
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

    # Key dimensions — overridable from CLI
    parser.add_argument("--port-width", type=float, default=PORT_WIDTH)
    parser.add_argument("--port-height", type=float, default=PORT_HEIGHT)
    parser.add_argument("--corner-radius", type=float, default=PORT_CORNER_RADIUS)
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--plate-thickness", type=float, default=PLATE_THICKNESS)
    parser.add_argument("--rim-thickness", type=float, default=RIM_THICKNESS)
    parser.add_argument("--rim-depth", type=float, default=RIM_DEPTH)
    parser.add_argument("--screw-dia", type=float, default=SCREW_HOLE_DIA)
    parser.add_argument("--screw-x", type=float, default=SCREW_OFFSET_X)
    parser.add_argument("--screw-y", type=float, default=SCREW_OFFSET_Y)

    args = parser.parse_args()

    # Build a kwargs dict with all dimensions; each stage function accepts
    # only the subset it cares about via its signature defaults.
    kwargs = dict(
        port_width=args.port_width,
        port_height=args.port_height,
        corner_radius=args.corner_radius,
        wall=args.wall,
        thickness=args.plate_thickness,
        plate_thickness=args.plate_thickness,
        rim_thickness=args.rim_thickness,
        rim_depth=args.rim_depth,
        screw_dia=args.screw_dia,
        screw_x=args.screw_x,
        screw_y=args.screw_y,
    )

    # Filter kwargs to only those the builder accepts
    builder = STAGES[args.stage]
    sig = inspect.signature(builder)
    filtered = {k: v for k, v in kwargs.items() if k in sig.parameters}
    body = builder(**filtered)

    name = f"dust_port_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
