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

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import on_build_plate  # noqa: E402

# Import geometry helpers from the profile test module
from profile_test import _build_quad_solid, _offset_vertices_inward  # noqa: E402

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

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
        result = on_build_plate(result.rotate((0, 0, 0), (1, 0, 0), 180))

    return result


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "faceplate": build_faceplate,
}

PARAMS = {
    # Vertex positions of the rim quadrilateral
    "ax": AX, "ay": AY,
    "bx": BX, "by": BY,
    "cx": CX, "cy": CY,
    "dx": DX, "dy": DY,

    # Corner fillets
    "fillet_a": FILLET_A,
    "fillet_b": FILLET_B,
    "fillet_c": FILLET_C,
    "fillet_d": FILLET_D,

    # Edge curvature
    "ab_bulge": (AB_BULGE, "Inward bulge (sagitta, mm) for the A-B edge. 0 = straight."),

    "wall": (WALL, "Wall thickness (outward from inner edge)."),
    "wall_height": (WALL_HEIGHT, "Height of the walls that wrap around the rim."),
    "cap_thickness": (CAP_THICKNESS, "Thickness of the solid cap on top."),

    # Screw hole
    "screw_x": (SCREW_X, "Screw hole center X coordinate."),
    "screw_y": (SCREW_Y, "Screw hole center Y coordinate."),
    "screw_diameter": (SCREW_DIAMETER, "Screw hole diameter."),

    # Port hole (quadrilateral cutout in the cap)
    "port_hole_ax": PORT_HOLE_AX, "port_hole_ay": PORT_HOLE_AY,
    "port_hole_bx": PORT_HOLE_BX, "port_hole_by": PORT_HOLE_BY,
    "port_hole_cx": PORT_HOLE_CX, "port_hole_cy": PORT_HOLE_CY,
    "port_hole_dx": PORT_HOLE_DX, "port_hole_dy": PORT_HOLE_DY,
    "port_hole_fillet": (PORT_HOLE_FILLET, "Fillet radius for port hole corners."),
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
