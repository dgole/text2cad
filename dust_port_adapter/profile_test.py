#!/usr/bin/env python3
"""
Dust Port Adapter — 2D outer rim profile test piece.

Generates a thin flat plate matching the outer perimeter of the flange/rim
around the saw's dust port.  Print it, hold it up to the saw, check fit.

The shape is an irregular quadrilateral with:
  - 4 mostly-straight sides
  - 3 corners that are close to 90° (with small fillets)
  - 1 corner (D, top-left) with significant rounding

Corner layout (looking at the port from outside the saw):

        D -------- C
        |          |
         \         |
          A ------ B

  A = bottom-left   (large fillet — the rounded corner)
  B = bottom-right  (~100°, slight fillet)
  C = top-right     (~95°, slight fillet)
  D = top-left      (~95°, slight fillet)

Parameterization is by vertex coordinates directly — measure the 4
corner positions relative to any convenient origin (e.g. bottom-left = 0,0).
This is simpler and more accurate than angles + side lengths when you
have calipers and a ruler on the real part.

Usage:
    python profile_test.py
    python profile_test.py --thickness 3
"""

from __future__ import annotations

import argparse
import math
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters — all dimensions in mm.
#
# Vertex positions: measure the outer rim of the flange.
# Origin at A (bottom-left), X to the right, Y up.
# ALL VALUES ARE PLACEHOLDERS — measure your saw!
# ---------------------------------------------------------------------------

# Vertices (x, y) of the INNER edge — the surface that sits against the rim.
# Outer edge is computed by offsetting outward by WALL.
AX, AY = 0.0, 0.0         # bottom-left (rounded corner)
BX, BY = 73.0, 39.0       # bottom-right
CX, CY = 70.0, 58.0       # top-right
DX, DY = 10.0, 58.0       # top-left

# Fillet radii at each corner
FILLET_A = 6.0             # large rounded corner
FILLET_B = 2.5             # small
FILLET_C = 2.5             # small
FILLET_D = 2.5             # small

# Edge curvature — inward bulge (sagitta) for the A→B edge.
# 0 = perfectly straight.  Positive = bows inward (toward polygon interior).
# This is the perpendicular distance from the chord midpoint to the arc apex.
AB_BULGE = 2.0             # mm — slight inward bow on the A→B edge

# Wall thickness for outline-only mode
WALL = 2.5

# Test plate thickness (just enough to be rigid for a fit check)
THICKNESS = 2.0


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _offset_vertices_inward(
    verts: List[Tuple[float, float]],
    offset: float,
) -> List[Tuple[float, float]]:
    """
    Offset each vertex inward (toward the polygon interior) by `offset` mm.

    For each vertex, we compute the inward-pointing bisector of its two
    adjacent edges, then move the vertex along that bisector.
    """
    n = len(verts)
    result = []
    for i in range(n):
        p_prev = verts[(i - 1) % n]
        p_curr = verts[i]
        p_next = verts[(i + 1) % n]

        # Edge vectors
        e1 = (p_curr[0] - p_prev[0], p_curr[1] - p_prev[1])
        e2 = (p_next[0] - p_curr[0], p_next[1] - p_curr[1])

        # Inward-pointing normals (for clockwise winding, inward = left of edge direction)
        # Left normal of a vector (dx, dy) is (-dy, dx)
        n1_len = math.sqrt(e1[0]**2 + e1[1]**2)
        n2_len = math.sqrt(e2[0]**2 + e2[1]**2)
        n1 = (-e1[1] / n1_len, e1[0] / n1_len)
        n2 = (-e2[1] / n2_len, e2[0] / n2_len)

        # Bisector of the two inward normals
        bx = n1[0] + n2[0]
        by = n1[1] + n2[1]
        b_len = math.sqrt(bx**2 + by**2)
        if b_len < 1e-9:
            # Edges are parallel; just use one normal
            bx, by = n1
            b_len = 1.0

        # The offset distance along the bisector needs to be scaled so that
        # the perpendicular distance from each edge is `offset`.
        # Scale factor = offset / cos(half_angle) = offset / (dot(bisector, n1))
        dot = (bx / b_len) * n1[0] + (by / b_len) * n1[1]
        if abs(dot) < 1e-9:
            dot = 1.0
        scaled_offset = offset / dot

        result.append((
            p_curr[0] + (bx / b_len) * scaled_offset,
            p_curr[1] + (by / b_len) * scaled_offset,
        ))
    return result


def _fillet_corner(
    p_prev: Tuple[float, float],
    p_corner: Tuple[float, float],
    p_next: Tuple[float, float],
    radius: float,
) -> Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float]]:
    """
    Given three consecutive vertices (prev → corner → next) and a fillet
    radius, compute:
      - tangent_start: the point on edge (prev→corner) where the arc begins
      - arc_center: center of the fillet arc
      - tangent_end: the point on edge (corner→next) where the arc ends

    The arc goes from tangent_start to tangent_end, curving towards the
    interior of the corner.
    """
    # Vectors from corner to prev and corner to next
    v1 = (p_prev[0] - p_corner[0], p_prev[1] - p_corner[1])
    v2 = (p_next[0] - p_corner[0], p_next[1] - p_corner[1])

    len1 = math.sqrt(v1[0]**2 + v1[1]**2)
    len2 = math.sqrt(v2[0]**2 + v2[1]**2)

    # Unit vectors
    u1 = (v1[0] / len1, v1[1] / len1)
    u2 = (v2[0] / len2, v2[1] / len2)

    # Half-angle between the two edges
    dot = u1[0] * u2[0] + u1[1] * u2[1]
    dot = max(-1.0, min(1.0, dot))  # clamp for numerical safety
    half_angle = math.acos(dot) / 2.0

    # Distance from corner to tangent points
    tan_dist = radius / math.tan(half_angle)

    # Tangent points
    t_start = (p_corner[0] + u1[0] * tan_dist, p_corner[1] + u1[1] * tan_dist)
    t_end = (p_corner[0] + u2[0] * tan_dist, p_corner[1] + u2[1] * tan_dist)

    # Arc center: along the angle bisector, at distance radius / sin(half_angle)
    bisector = (u1[0] + u2[0], u1[1] + u2[1])
    bis_len = math.sqrt(bisector[0]**2 + bisector[1]**2)
    bisector = (bisector[0] / bis_len, bisector[1] / bis_len)
    center_dist = radius / math.sin(half_angle)
    arc_center = (
        p_corner[0] + bisector[0] * center_dist,
        p_corner[1] + bisector[1] * center_dist,
    )

    return t_start, arc_center, t_end


def _build_quad_solid(
    verts: List[Tuple[float, float]],
    fillets: List[float],
    thickness: float,
    edge_bulges: List[float] = None,
) -> cq.Workplane:
    """
    Build a thin extruded solid from a filleted quadrilateral.
    verts: 4 (x,y) vertices in order.  fillets: radius per corner.
    edge_bulges: per-edge sagitta values (inward bulge).  edge_bulges[i] is
    for the edge from vertex i to vertex i+1.  0 or None = straight line.
    """
    n = len(verts)
    if edge_bulges is None:
        edge_bulges = [0.0] * n

    corners = []
    for i in range(n):
        p_prev = verts[(i - 1) % n]
        p_corner = verts[i]
        p_next = verts[(i + 1) % n]
        r = fillets[i]
        if r > 0.01:
            t_start, arc_ctr, t_end = _fillet_corner(p_prev, p_corner, p_next, r)
            corners.append({
                "fillet": True,
                "t_start": t_start,
                "arc_center": arc_ctr,
                "t_end": t_end,
                "radius": r,
            })
        else:
            corners.append({
                "fillet": False,
                "point": p_corner,
            })

    first = corners[0]
    start = first["t_start"] if first["fillet"] else first["point"]
    wp = cq.Workplane("XY").moveTo(start[0], start[1])

    for i in range(n):
        c = corners[i]
        c_next = corners[(i + 1) % n]

        if c["fillet"]:
            mid_x = (c["t_start"][0] + c["t_end"][0]) / 2
            mid_y = (c["t_start"][1] + c["t_end"][1]) / 2
            dx_cm = mid_x - c["arc_center"][0]
            dy_cm = mid_y - c["arc_center"][1]
            dist_cm = math.sqrt(dx_cm**2 + dy_cm**2)
            if dist_cm > 1e-9:
                arc_mid = (
                    c["arc_center"][0] + dx_cm / dist_cm * c["radius"],
                    c["arc_center"][1] + dy_cm / dist_cm * c["radius"],
                )
            else:
                arc_mid = (mid_x, mid_y)

            wp = wp.threePointArc(arc_mid, c["t_end"])

        # End-point of the straight (or bulged) segment to the next corner
        target = c_next["t_start"] if c_next["fillet"] else c_next["point"]

        bulge = edge_bulges[i]
        if abs(bulge) > 1e-6:
            # Current pen position = c["t_end"] if filleted, else c["point"]
            pen = c["t_end"] if c["fillet"] else c["point"]

            # Chord midpoint
            cmx = (pen[0] + target[0]) / 2.0
            cmy = (pen[1] + target[1]) / 2.0

            # Edge direction vector (pen → target)
            edx = target[0] - pen[0]
            edy = target[1] - pen[1]
            edge_len = math.sqrt(edx**2 + edy**2)

            if edge_len > 1e-9:
                # Inward normal: for our CCW-ish winding the polygon interior
                # is to the LEFT of the edge direction, so the inward-pointing
                # perpendicular is (-edy, edx) normalised.
                inx = -edy / edge_len
                iny =  edx / edge_len

                # Arc midpoint displaced inward by the bulge sagitta
                arc_edge_mid = (cmx + inx * bulge, cmy + iny * bulge)
                wp = wp.threePointArc(arc_edge_mid, target)
            else:
                wp = wp.lineTo(target[0], target[1])
        else:
            wp = wp.lineTo(target[0], target[1])

    return wp.close().extrude(thickness)


def build_profile_plate(
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
    thickness: float = THICKNESS,
) -> cq.Workplane:
    """
    Build a thin outline (frame) matching the outer rim of the flange.
    The vertex coordinates define the INNER edge (the surface that sits
    against the rim). The outer edge is offset outward by wall thickness.
    """
    inner_verts = [(ax, ay), (bx, by), (cx, cy), (dx, dy)]
    inner_fillets = [fillet_a, fillet_b, fillet_c, fillet_d]

    # Edge bulges: index 0 = A→B edge, 1 = B→C, 2 = C→D, 3 = D→A
    inner_bulges = [ab_bulge, 0.0, 0.0, 0.0]

    # Offset outward (negative inward = outward)
    outer_verts = _offset_vertices_inward(inner_verts, -wall)
    outer_fillets = [f + wall for f in inner_fillets]
    # Outer edge uses the SAME sagitta as inner — both bow inward by the same
    # amount from their own chord.  The wall thickness is already set by the
    # vertex offset, so matching the sagitta keeps the wall uniform.
    outer_bulges = [ab_bulge, 0.0, 0.0, 0.0]

    outer_solid = _build_quad_solid(outer_verts, outer_fillets, thickness, outer_bulges)
    inner_solid = _build_quad_solid(inner_verts, inner_fillets, thickness, inner_bulges)

    return outer_solid.cut(inner_solid)


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
                        help="Inward bulge (sagitta, mm) for the A→B edge. 0=straight.")

    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--thickness", type=float, default=THICKNESS)

    args = parser.parse_args()

    body = build_profile_plate(
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
        thickness=args.thickness,
    )

    to_stl(body, "dust_port_outer_rim_profile", output_dir=args.output_dir)


if __name__ == "__main__":
    main()
