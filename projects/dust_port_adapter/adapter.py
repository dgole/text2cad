#!/usr/bin/env python3
"""
Dust Port Adapter — complete adapter with curved transition tube.

Builds the full adapter: faceplate (clips onto the saw's dust port rim)
and a curved transition tube that morphs from the irregular port hole
to a circular hose connection while simultaneously curving from vertical
toward the exit direction.

Stages:
    transition_test — faceplate + curved transition (quad → circle along arc)
    full            — faceplate + curved transition + female hose socket

Usage:
    python adapter.py full
    python adapter.py transition_test
    python adapter.py full --hose-od 38 --arc-angle-deg 90
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

# Import builders from sibling modules
from faceplate import build_faceplate  # noqa: E402
from profile_test import _build_quad_solid, _fillet_corner  # noqa: E402

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config
# ---------------------------------------------------------------------------

# Faceplate dimensions (needed for positioning the tube)
WALL_HEIGHT = CFG["faceplate"]["wall_height"]
CAP_THICKNESS = CFG["faceplate"]["cap_thickness"]

# Port hole shape (the quad cutout in the cap — tube starts here)
_ph = CFG["faceplate"]["port_hole"]
PORT_HOLE_VERTS = [tuple(_ph[k]) for k in ("A", "B", "C", "D")]
PORT_HOLE_FILLET = _ph["fillet_radius"]

# Transition tube parameters
_tr = CFG["transition"]
HOSE_OD = _tr["hose_od"]
HOSE_TOLERANCE = _tr["hose_tolerance"]
SOCKET_DEPTH = _tr["socket_depth"]
TUBE_WALL = _tr["tube_wall"]
ARC_RADIUS = _tr["arc_radius"]
ARC_ANGLE_DEG = _tr["arc_angle_deg"]
ARC_DIRECTION_DEG = _tr["arc_direction_deg"]
NUM_LOFT_STATIONS = _tr["num_loft_stations"]
NUM_PROFILE_POINTS = _tr["num_profile_points"]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _sample_quad_outline(
    verts: List[Tuple[float, float]],
    fillet_r: float,
    num_points: int,
) -> List[Tuple[float, float]]:
    """
    Sample `num_points` evenly-spaced (by arc length) around a filleted
    quadrilateral defined by `verts` with uniform fillet radius.

    Returns a list of (x, y) points walking CCW around the shape.
    """
    n = len(verts)

    # --- Build a dense polyline of the outline (corners + fillets) ---
    segments = []  # each segment is a list of (x, y) points
    for i in range(n):
        p_prev = verts[(i - 1) % n]
        p_curr = verts[i]
        p_next = verts[(i + 1) % n]

        if fillet_r > 0.01:
            t_start, arc_center, t_end = _fillet_corner(
                p_prev, p_curr, p_next, fillet_r,
            )
            # Sample the fillet arc
            arc_points = _sample_arc(t_start, arc_center, t_end, fillet_r, 16)
            segments.append(arc_points)
        else:
            segments.append([p_curr])

    # Between each fillet's t_end and the next fillet's t_start, there's
    # a straight edge. Interleave those.
    outline = []
    for i in range(n):
        seg = segments[i]
        outline.extend(seg)
        # Straight edge from end of this fillet to start of next fillet
        next_seg = segments[(i + 1) % n]
        edge_start = seg[-1]
        edge_end = next_seg[0]
        # Add a few intermediate points along the straight edge
        for k in range(1, 5):
            t = k / 5.0
            outline.append((
                edge_start[0] + t * (edge_end[0] - edge_start[0]),
                edge_start[1] + t * (edge_end[1] - edge_start[1]),
            ))

    # --- Compute cumulative arc lengths ---
    cum_len = [0.0]
    for i in range(1, len(outline)):
        dx = outline[i][0] - outline[i - 1][0]
        dy = outline[i][1] - outline[i - 1][1]
        cum_len.append(cum_len[-1] + math.sqrt(dx * dx + dy * dy))
    # Close the loop
    dx = outline[0][0] - outline[-1][0]
    dy = outline[0][1] - outline[-1][1]
    total_len = cum_len[-1] + math.sqrt(dx * dx + dy * dy)

    # --- Resample at equal arc-length intervals ---
    result = []
    for j in range(num_points):
        target_len = (j / num_points) * total_len
        # Find the segment containing this arc length
        idx = 0
        for k in range(len(cum_len) - 1):
            if cum_len[k + 1] >= target_len:
                idx = k
                break
        else:
            idx = len(cum_len) - 2

        seg_start = cum_len[idx]
        seg_end = cum_len[idx + 1] if idx + 1 < len(cum_len) else total_len
        seg_len = seg_end - seg_start
        if seg_len < 1e-9:
            frac = 0.0
        else:
            frac = (target_len - seg_start) / seg_len

        p1 = outline[idx]
        p2 = outline[(idx + 1) % len(outline)]
        result.append((
            p1[0] + frac * (p2[0] - p1[0]),
            p1[1] + frac * (p2[1] - p1[1]),
        ))

    return result


def _sample_arc(
    t_start: Tuple[float, float],
    center: Tuple[float, float],
    t_end: Tuple[float, float],
    radius: float,
    num_samples: int,
) -> List[Tuple[float, float]]:
    """Sample points along a circular arc from t_start to t_end."""
    angle_start = math.atan2(
        t_start[1] - center[1], t_start[0] - center[0],
    )
    angle_end = math.atan2(
        t_end[1] - center[1], t_end[0] - center[0],
    )

    # Ensure we go in the shorter direction (CCW)
    if angle_end < angle_start:
        angle_end += 2 * math.pi
    # But if that makes it > 180°, go the other way
    if angle_end - angle_start > math.pi:
        angle_end -= 2 * math.pi

    points = []
    for i in range(num_samples):
        t = i / max(num_samples - 1, 1)
        angle = angle_start + t * (angle_end - angle_start)
        points.append((
            center[0] + radius * math.cos(angle),
            center[1] + radius * math.sin(angle),
        ))
    return points


def _sample_circle(
    cx: float, cy: float, radius: float,
    num_points: int,
    start_angle: float = 0.0,
) -> List[Tuple[float, float]]:
    """Sample `num_points` evenly around a circle."""
    return [
        (
            cx + radius * math.cos(start_angle + 2 * math.pi * j / num_points),
            cy + radius * math.sin(start_angle + 2 * math.pi * j / num_points),
        )
        for j in range(num_points)
    ]


def _quad_centroid(
    verts: List[Tuple[float, float]],
) -> Tuple[float, float]:
    """Centroid of a polygon (average of vertices)."""
    cx = sum(v[0] for v in verts) / len(verts)
    cy = sum(v[1] for v in verts) / len(verts)
    return cx, cy


def _make_wire_from_points(
    points_2d: List[Tuple[float, float]],
    z: float,
) -> cq.Wire:
    """Build a closed wire from 2D points at the given Z height."""
    pts_3d = [(x, y, z) for x, y in points_2d]
    edges = []
    for i in range(len(pts_3d)):
        p1 = cq.Vector(*pts_3d[i])
        p2 = cq.Vector(*pts_3d[(i + 1) % len(pts_3d)])
        edges.append(cq.Edge.makeLine(p1, p2))
    return cq.Wire.assembleEdges(edges)


def _offset_quad_outline(
    verts: List[Tuple[float, float]],
    fillet_r: float,
    offset: float,
    num_points: int,
    centroid: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """
    Offset a quad outline outward (positive offset) or inward (negative).
    Simple approach: scale each sampled point away from the centroid.
    """
    sampled = _sample_quad_outline(verts, fillet_r, num_points)
    cx, cy = centroid
    result = []
    for px, py in sampled:
        dx = px - cx
        dy = py - cy
        dist = math.sqrt(dx * dx + dy * dy)
        if dist < 1e-9:
            result.append((px, py))
            continue
        # Move point outward by `offset` along the radial direction
        result.append((
            px + (dx / dist) * offset,
            py + (dy / dist) * offset,
        ))
    return result


# ---------------------------------------------------------------------------
# Curved transition builder: quad → circle along an arc path
# ---------------------------------------------------------------------------

def _rodrigues_rotate(
    point: Tuple[float, float, float],
    axis: Tuple[float, float, float],
    angle: float,
) -> Tuple[float, float, float]:
    """Rotate `point` around `axis` (unit vector) by `angle` radians."""
    px, py, pz = point
    kx, ky, kz = axis
    c = math.cos(angle)
    s = math.sin(angle)
    dot = kx * px + ky * py + kz * pz
    # k × p
    cx_ = ky * pz - kz * py
    cy_ = kz * px - kx * pz
    cz_ = kx * py - ky * px
    return (
        px * c + cx_ * s + kx * dot * (1 - c),
        py * c + cy_ * s + ky * dot * (1 - c),
        pz * c + cz_ * s + kz * dot * (1 - c),
    )


def build_curved_transition(
    port_hole_verts: List[Tuple[float, float]],
    port_hole_fillet: float,
    hose_od: float,
    hose_tolerance: float,
    tube_wall: float,
    arc_radius: float,
    arc_angle_deg: float,
    arc_direction_deg: float,
    num_stations: int,
    num_points: int,
    z_base: float,
) -> Tuple[cq.Workplane, Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Build the hollow curved transition from the port hole quad to a circle.

    The tube starts at z_base (top of the faceplate cap) pointing +Z, and
    curves along a circular arc toward the exit direction.  The cross-section
    morphs from the port hole quad shape to a circle over the arc.

    Returns:
        (solid, exit_point, exit_direction) — the solid geometry plus the
        3D position and unit-vector direction at the arc exit (for attaching
        the socket).
    """
    centroid = _quad_centroid(port_hole_verts)
    cx, cy = centroid
    inner_radius = (hose_od + hose_tolerance) / 2.0
    outer_radius = inner_radius + tube_wall

    arc_angle = math.radians(arc_angle_deg)
    alpha = math.radians(arc_direction_deg)

    # Exit direction in XY plane (the horizontal direction the tube curves toward)
    d_exit = (-math.cos(alpha), -math.sin(alpha), 0.0)

    # Binormal: perpendicular to the arc plane (constant along the arc)
    # B = d_exit × Z_hat
    binormal = (-math.sin(alpha), math.cos(alpha), 0.0)

    # Sample the port hole quad (inner and outer)
    inner_quad = _sample_quad_outline(
        port_hole_verts, port_hole_fillet, num_points,
    )
    outer_quad = _offset_quad_outline(
        port_hole_verts, port_hole_fillet, tube_wall, num_points, centroid,
    )

    # Compute start angle for circle sampling (align with first quad point)
    first_quad_pt = inner_quad[0]
    start_angle = math.atan2(
        first_quad_pt[1] - cy,
        first_quad_pt[0] - cx,
    )

    # Target circles
    inner_circle = _sample_circle(cx, cy, inner_radius, num_points, start_angle)
    outer_circle = _sample_circle(cx, cy, outer_radius, num_points, start_angle)

    # Arc start point
    p0 = (cx, cy, z_base)

    # --- Build wires at each station along the arc ---
    outer_wires = []
    inner_wires = []
    for i in range(num_stations + 1):
        # phi = angle along the arc (0 at start, arc_angle at end)
        phi = arc_angle * i / num_stations
        # t = interpolation parameter for quad→circle morph (0→1)
        t = i / num_stations

        # Interpolate 2D cross-section (quad→circle) centered at centroid
        outer_pts_2d = [
            (
                (1 - t) * oq[0] + t * oc[0],
                (1 - t) * oq[1] + t * oc[1],
            )
            for oq, oc in zip(outer_quad, outer_circle)
        ]
        inner_pts_2d = [
            (
                (1 - t) * iq[0] + t * ic[0],
                (1 - t) * iq[1] + t * ic[1],
            )
            for iq, ic in zip(inner_quad, inner_circle)
        ]

        # Arc centerline position at phi:
        #   Position = P0 + R(1 - cos φ) * d_exit + R sin φ * Z_hat
        arc_pos = (
            p0[0] + arc_radius * (1 - math.cos(phi)) * d_exit[0],
            p0[1] + arc_radius * (1 - math.cos(phi)) * d_exit[1],
            p0[2] + arc_radius * math.sin(phi),
        )

        # Transform 2D points to 3D:
        # - Subtract centroid to get relative positions
        # - Treat as 3D points in XY plane: (dx, dy, 0)
        # - Rotate by phi around the binormal axis (pivoting at arc start)
        # - Translate to arc position
        def transform(pts_2d: List[Tuple[float, float]]) -> List[Tuple[float, float, float]]:
            pts_3d = []
            for px, py in pts_2d:
                # Relative to centroid
                dx, dy = px - cx, py - cy
                # Rotate (dx, dy, 0) by -phi around binormal so the
                # cross-section stays perpendicular to the arc tangent
                rx, ry, rz = _rodrigues_rotate((dx, dy, 0.0), binormal, -phi)
                pts_3d.append((
                    arc_pos[0] + rx,
                    arc_pos[1] + ry,
                    arc_pos[2] + rz,
                ))
            return pts_3d

        outer_pts_3d = transform(outer_pts_2d)
        inner_pts_3d = transform(inner_pts_2d)

        outer_wires.append(_make_wire_from_points_3d(outer_pts_3d))
        inner_wires.append(_make_wire_from_points_3d(inner_pts_3d))

    # --- Loft outer and inner shells ---
    outer_solid = cq.Solid.makeLoft(outer_wires)
    inner_solid = cq.Solid.makeLoft(inner_wires)

    # Hollow tube = outer - inner
    # The boolean cut on non-coplanar lofts may produce a Compound;
    # .solids() extracts the actual solid(s) for downstream .union().
    result = cq.Workplane("XY").add(outer_solid).cut(
        cq.Workplane("XY").add(inner_solid)
    ).solids()

    # --- Compute exit point and direction ---
    exit_point = (
        p0[0] + arc_radius * (1 - math.cos(arc_angle)) * d_exit[0],
        p0[1] + arc_radius * (1 - math.cos(arc_angle)) * d_exit[1],
        p0[2] + arc_radius * math.sin(arc_angle),
    )
    # Tangent at exit: sin(arc_angle) * d_exit + cos(arc_angle) * Z_hat
    exit_dir = (
        math.sin(arc_angle) * d_exit[0],
        math.sin(arc_angle) * d_exit[1],
        math.cos(arc_angle),
    )

    return result, exit_point, exit_dir


def _make_wire_from_points_3d(
    points_3d: List[Tuple[float, float, float]],
) -> cq.Wire:
    """Build a closed wire from 3D points."""
    edges = []
    for i in range(len(points_3d)):
        p1 = cq.Vector(*points_3d[i])
        p2 = cq.Vector(*points_3d[(i + 1) % len(points_3d)])
        edges.append(cq.Edge.makeLine(p1, p2))
    return cq.Wire.assembleEdges(edges)


# ---------------------------------------------------------------------------
# Socket builder: female hose socket
# ---------------------------------------------------------------------------

def build_socket(
    exit_x: float,
    exit_y: float,
    exit_z: float,
    exit_dir: Tuple[float, float, float],
    hose_od: float,
    hose_tolerance: float,
    tube_wall: float,
    socket_depth: float,
) -> cq.Workplane:
    """
    Build a short cylindrical female socket extending along exit_dir.

    The hose slides into this socket.  Inner diameter fits the hose OD.
    """
    inner_r = (hose_od + hose_tolerance) / 2.0
    outer_r = inner_r + tube_wall

    # Build a workplane perpendicular to the exit direction.
    # Find an xDir perpendicular to exit_dir.
    ex, ey, ez = exit_dir
    # Use whichever world axis is least parallel to exit_dir
    if abs(ez) < 0.9:
        x_dir = cq.Vector(-ey, ex, 0).normalized()
    else:
        x_dir = cq.Vector(0, -ez, ey).normalized()

    socket_plane = cq.Plane(
        origin=cq.Vector(exit_x, exit_y, exit_z),
        xDir=x_dir,
        normal=cq.Vector(*exit_dir),
    )

    outer_cyl = cq.Workplane(socket_plane).circle(outer_r).extrude(socket_depth)
    inner_cyl = cq.Workplane(socket_plane).circle(inner_r).extrude(socket_depth)

    return outer_cyl.cut(inner_cyl)


# ---------------------------------------------------------------------------
# Stage builders
# ---------------------------------------------------------------------------

def build_adapter(
    stage: str = "full",
    hose_od: float = HOSE_OD,
    hose_tolerance: float = HOSE_TOLERANCE,
    socket_depth: float = SOCKET_DEPTH,
    tube_wall: float = TUBE_WALL,
    arc_radius: float = ARC_RADIUS,
    arc_angle_deg: float = ARC_ANGLE_DEG,
    arc_direction_deg: float = ARC_DIRECTION_DEG,
    num_stations: int = NUM_LOFT_STATIONS,
    num_points: int = NUM_PROFILE_POINTS,
) -> cq.Workplane:
    """Build the adapter at the specified stage."""

    # Z coordinate of the top of the faceplate cap (in build orientation)
    z_cap_top = WALL_HEIGHT + CAP_THICKNESS

    # 1. Faceplate (no flip — we flip the whole assembly at the end)
    print("  Building faceplate...")
    result = build_faceplate(flip_for_print=False)

    # 2. Curved transition (quad → circle along arc)
    print("  Building curved transition...")
    transition, exit_point, exit_dir = build_curved_transition(
        port_hole_verts=PORT_HOLE_VERTS,
        port_hole_fillet=PORT_HOLE_FILLET,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        arc_radius=arc_radius,
        arc_angle_deg=arc_angle_deg,
        arc_direction_deg=arc_direction_deg,
        num_stations=num_stations,
        num_points=num_points,
        z_base=z_cap_top - 1.0,  # overlap into cap for reliable boolean union
    )
    result = result.union(transition)

    if stage == "transition_test":
        return _orient_for_print(result)

    # 3. Hose socket (extends from the arc exit)
    print("  Building hose socket...")
    socket = build_socket(
        exit_x=exit_point[0],
        exit_y=exit_point[1],
        exit_z=exit_point[2],
        exit_dir=exit_dir,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        socket_depth=socket_depth,
    )
    result = result.union(socket)

    return _orient_for_print(result)


def _orient_for_print(body: cq.Workplane) -> cq.Workplane:
    """Shift the part so the lowest point sits at Z = 0."""
    bb = body.val().BoundingBox()
    return body.translate((0, 0, -bb.zmin))


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "transition_test": "Faceplate + curved transition (quad → circle along arc)",
    "full": "Complete adapter: faceplate + curved transition + hose socket",
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "stage",
        choices=STAGES.keys(),
        help="Build stage: " + "; ".join(
            f"{k} = {v}" for k, v in STAGES.items()
        ),
    )
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))
    parser.add_argument("--hose-od", type=float, default=HOSE_OD,
                        help="Hose outer diameter (mm).")
    parser.add_argument("--hose-tolerance", type=float, default=HOSE_TOLERANCE)
    parser.add_argument("--socket-depth", type=float, default=SOCKET_DEPTH)
    parser.add_argument("--tube-wall", type=float, default=TUBE_WALL)
    parser.add_argument("--arc-radius", type=float, default=ARC_RADIUS,
                        help="Centerline radius of the curved path (mm).")
    parser.add_argument("--arc-angle-deg", type=float, default=ARC_ANGLE_DEG,
                        help="Total sweep angle (degrees). 90=horizontal exit.")
    parser.add_argument("--arc-direction-deg", type=float, default=ARC_DIRECTION_DEG,
                        help="Curve direction (degrees). 0=toward A-D edge, positive=toward A-B.")
    parser.add_argument("--num-stations", type=int, default=NUM_LOFT_STATIONS)
    parser.add_argument("--num-points", type=int, default=NUM_PROFILE_POINTS)

    args = parser.parse_args()

    print(f"Building stage: {args.stage} — {STAGES[args.stage]}")
    body = build_adapter(
        stage=args.stage,
        hose_od=args.hose_od,
        hose_tolerance=args.hose_tolerance,
        socket_depth=args.socket_depth,
        tube_wall=args.tube_wall,
        arc_radius=args.arc_radius,
        arc_angle_deg=args.arc_angle_deg,
        arc_direction_deg=args.arc_direction_deg,
        num_stations=args.num_stations,
        num_points=args.num_points,
    )

    name = f"dust_port_adapter_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)
    print(f"Done → {Path(args.output_dir) / (name + '.stl')}")


if __name__ == "__main__":
    main()
