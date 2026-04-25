#!/usr/bin/env python3
"""
Dust Port Adapter — faceplate with walls.

Builds the adapter body: walls that drop over the saw's dust port flange/rim,
capped with a solid plate on top.  The wall profile matches the outer rim
shape from profile_test.py.

Side view (cross section):

        cap (solid plate on top)
    ┌─────────────────────────┐  ← Z = WALL_HEIGHT + CAP_THICKNESS
    │█████████████████████████│
    ├───┐                 ┌───┤  ← Z = WALL_HEIGHT
    │   │  hollow inside  │   │
    │   │  (fits over rim)│   │
    │   │                 │   │
    └───┘                 └───┘  ← Z = 0

The walls are the existing rim profile (outer minus inner) extruded to
WALL_HEIGHT.  The cap is the full outer profile extruded by CAP_THICKNESS,
sitting on top of the walls.

Later steps will cut holes in the cap for the dust port opening and screw.

Usage:
    python faceplate.py
    python faceplate.py --wall-height 8 --cap-thickness 3
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

# Import geometry helpers from the profile test module
from profile_test import _build_quad_solid, _offset_vertices_inward  # noqa: E402

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

AX, AY = CFG["vertices"]["A"]
BX, BY = CFG["vertices"]["B"]
CX, CY = CFG["vertices"]["C"]
DX, DY = CFG["vertices"]["D"]

FILLET_A = CFG["fillets"]["A"]
FILLET_B = CFG["fillets"]["B"]
FILLET_C = CFG["fillets"]["C"]
FILLET_D = CFG["fillets"]["D"]

AB_BULGE = CFG["ab_bulge"]
WALL = CFG["wall"]

_fp = CFG["faceplate"]
WALL_HEIGHT = _fp["wall_height"]
CAP_THICKNESS = _fp["cap_thickness"]
SCREW_X = _fp["screw_x"]
SCREW_Y = _fp["screw_y"]
SCREW_DIAMETER = _fp["screw_diameter"]

# Port hole — quadrilateral cutout through the cap
_ph = _fp["port_hole"]
PORT_HOLE_AX, PORT_HOLE_AY = _ph["A"]
PORT_HOLE_BX, PORT_HOLE_BY = _ph["B"]
PORT_HOLE_CX, PORT_HOLE_CY = _ph["C"]
PORT_HOLE_DX, PORT_HOLE_DY = _ph["D"]
PORT_HOLE_FILLET = _ph["fillet_radius"]


# ---------------------------------------------------------------------------
# Builder
# ---------------------------------------------------------------------------

def build_faceplate(
    ax: float = AX, ay: float = AY,
    bx: float = BX, by: float = BY,
    cx: float = CX, cy: float = CY,
    dx: float = DX, dy: float = DY,
    fillet_a: float = FILLET_A,
    fillet_b: float = FILLET_B,
    fillet_c: float = FILLET_C,
    fillet_d: float = FILLET_D,
    ab_bulge: float = AB_BULGE,
    wall: float = WALL,
    wall_height: float = WALL_HEIGHT,
    cap_thickness: float = CAP_THICKNESS,
    screw_x: float = SCREW_X,
    screw_y: float = SCREW_Y,
    screw_diameter: float = SCREW_DIAMETER,
    port_hole_ax: float = PORT_HOLE_AX, port_hole_ay: float = PORT_HOLE_AY,
    port_hole_bx: float = PORT_HOLE_BX, port_hole_by: float = PORT_HOLE_BY,
    port_hole_cx: float = PORT_HOLE_CX, port_hole_cy: float = PORT_HOLE_CY,
    port_hole_dx: float = PORT_HOLE_DX, port_hole_dy: float = PORT_HOLE_DY,
    port_hole_fillet: float = PORT_HOLE_FILLET,
    flip_for_print: bool = True,
) -> cq.Workplane:
    """
    Build the faceplate: walls around the rim + solid cap on top.

    The vertex coordinates define the INNER edge (against the rim).
    The outer edge is offset outward by `wall`.
    """
    inner_verts = [(ax, ay), (bx, by), (cx, cy), (dx, dy)]
    inner_fillets = [fillet_a, fillet_b, fillet_c, fillet_d]
    inner_bulges = [ab_bulge, 0.0, 0.0, 0.0]

    outer_verts = _offset_vertices_inward(inner_verts, -wall)
    outer_fillets = [f + wall for f in inner_fillets]
    outer_bulges = [ab_bulge, 0.0, 0.0, 0.0]

    # --- Walls: outer minus inner, extruded to wall_height ---
    outer_wall = _build_quad_solid(outer_verts, outer_fillets, wall_height, outer_bulges)
    inner_void = _build_quad_solid(inner_verts, inner_fillets, wall_height, inner_bulges)
    walls = outer_wall.cut(inner_void)

    # --- Cap: full outer solid, extruded by cap_thickness, on top of walls ---
    cap = _build_quad_solid(outer_verts, outer_fillets, cap_thickness, outer_bulges)
    cap = cap.translate((0, 0, wall_height))

    # --- Union walls + cap ---
    result = walls.union(cap)

    # --- Screw hole: cut through the cap ---
    screw_hole = (
        cq.Workplane("XY")
        .transformed(offset=(screw_x, screw_y, wall_height - 1))
        .circle(screw_diameter / 2.0)
        .extrude(cap_thickness + 2)  # generous to ensure full punch-through
    )
    result = result.cut(screw_hole)

    # --- Port hole: quadrilateral cutout through the cap ---
    port_hole_verts = [
        (port_hole_ax, port_hole_ay),
        (port_hole_bx, port_hole_by),
        (port_hole_cx, port_hole_cy),
        (port_hole_dx, port_hole_dy),
    ]
    port_hole_fillets = [port_hole_fillet] * 4
    # Build the quad solid starting just below the cap and punching through
    port_hole_solid = _build_quad_solid(
        port_hole_verts, port_hole_fillets,
        thickness=cap_thickness + 2,  # generous for full punch-through
        edge_bulges=[0.0, 0.0, 0.0, 0.0],
    )
    port_hole_solid = port_hole_solid.translate((0, 0, wall_height - 1))
    result = result.cut(port_hole_solid)

    if flip_for_print:
        # Flip upside-down so the cap is on the bottom (print-bed side) and the
        # walls open upward.  Then shift so the lowest point sits at Z = 0.
        result = result.rotate((0, 0, 0), (1, 0, 0), 180)
        bb = result.val().BoundingBox()
        result = result.translate((0, 0, -bb.zmin))

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))

    # Vertex positions
    parser.add_argument("--ax", type=float, default=AX)
    parser.add_argument("--ay", type=float, default=AY)
    parser.add_argument("--bx", type=float, default=BX)
    parser.add_argument("--by", type=float, default=BY)
    parser.add_argument("--cx", type=float, default=CX)
    parser.add_argument("--cy", type=float, default=CY)
    parser.add_argument("--dx", type=float, default=DX)
    parser.add_argument("--dy", type=float, default=DY)

    # Fillets
    parser.add_argument("--fillet-a", type=float, default=FILLET_A)
    parser.add_argument("--fillet-b", type=float, default=FILLET_B)
    parser.add_argument("--fillet-c", type=float, default=FILLET_C)
    parser.add_argument("--fillet-d", type=float, default=FILLET_D)

    # Edge curvature
    parser.add_argument("--ab-bulge", type=float, default=AB_BULGE,
                        help="Inward bulge (sagitta, mm) for the A→B edge.")

    # Wall / structure
    parser.add_argument("--wall", type=float, default=WALL,
                        help="Wall thickness (outward from inner edge).")
    parser.add_argument("--wall-height", type=float, default=WALL_HEIGHT,
                        help="Height of the walls that wrap around the rim.")
    parser.add_argument("--cap-thickness", type=float, default=CAP_THICKNESS,
                        help="Thickness of the solid cap on top.")

    # Screw hole
    parser.add_argument("--screw-x", type=float, default=SCREW_X,
                        help="Screw hole center X coordinate.")
    parser.add_argument("--screw-y", type=float, default=SCREW_Y,
                        help="Screw hole center Y coordinate.")
    parser.add_argument("--screw-diameter", type=float, default=SCREW_DIAMETER,
                        help="Screw hole diameter.")

    # Port hole (quadrilateral cutout)
    parser.add_argument("--port-hole-ax", type=float, default=PORT_HOLE_AX)
    parser.add_argument("--port-hole-ay", type=float, default=PORT_HOLE_AY)
    parser.add_argument("--port-hole-bx", type=float, default=PORT_HOLE_BX)
    parser.add_argument("--port-hole-by", type=float, default=PORT_HOLE_BY)
    parser.add_argument("--port-hole-cx", type=float, default=PORT_HOLE_CX)
    parser.add_argument("--port-hole-cy", type=float, default=PORT_HOLE_CY)
    parser.add_argument("--port-hole-dx", type=float, default=PORT_HOLE_DX)
    parser.add_argument("--port-hole-dy", type=float, default=PORT_HOLE_DY)
    parser.add_argument("--port-hole-fillet", type=float, default=PORT_HOLE_FILLET,
                        help="Fillet radius for port hole corners.")

    args = parser.parse_args()

    body = build_faceplate(
        ax=args.ax, ay=args.ay,
        bx=args.bx, by=args.by,
        cx=args.cx, cy=args.cy,
        dx=args.dx, dy=args.dy,
        fillet_a=args.fillet_a,
        fillet_b=args.fillet_b,
        fillet_c=args.fillet_c,
        fillet_d=args.fillet_d,
        ab_bulge=args.ab_bulge,
        wall=args.wall,
        wall_height=args.wall_height,
        cap_thickness=args.cap_thickness,
        screw_x=args.screw_x,
        screw_y=args.screw_y,
        screw_diameter=args.screw_diameter,
        port_hole_ax=args.port_hole_ax, port_hole_ay=args.port_hole_ay,
        port_hole_bx=args.port_hole_bx, port_hole_by=args.port_hole_by,
        port_hole_cx=args.port_hole_cx, port_hole_cy=args.port_hole_cy,
        port_hole_dx=args.port_hole_dx, port_hole_dy=args.port_hole_dy,
        port_hole_fillet=args.port_hole_fillet,
    )

    to_stl(body, "dust_port_faceplate", output_dir=args.output_dir)


if __name__ == "__main__":
    main()
