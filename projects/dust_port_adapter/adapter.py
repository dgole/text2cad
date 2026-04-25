#!/usr/bin/env python3
"""
Dust Port Adapter — complete adapter with transition tube.

Builds the full adapter: faceplate (clips onto the saw's dust port rim),
a transition loft (morphs from the irregular port hole to a circle),
a 90-degree elbow, and a female hose socket.

Stages:
    loft_test   — faceplate + straight transition loft (quad → circle)
    elbow_test  — faceplate + loft + 90° elbow
    full        — faceplate + loft + elbow + hose socket

Usage:
    python adapter.py full
    python adapter.py loft_test
    python adapter.py full --hose-od 38
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
STRAIGHT_LENGTH = _tr["straight_length"]
BEND_RADIUS = _tr["bend_radius"]
BEND_DIRECTION_DEG = _tr["bend_direction_deg"]
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
# Loft builder: quad → circle transition
# ---------------------------------------------------------------------------

def build_transition_loft(
    port_hole_verts: List[Tuple[float, float]],
    port_hole_fillet: float,
    hose_od: float,
    hose_tolerance: float,
    tube_wall: float,
    straight_length: float,
    num_stations: int,
    num_points: int,
    z_base: float,
) -> cq.Workplane:
    """
    Build the hollow transition loft from the port hole quad to a circle.

    The loft starts at z_base (top of the faceplate cap) and extends upward
    by straight_length.  The cross-section morphs from the port hole shape
    to a circle sized for the hose.
    """
    centroid = _quad_centroid(port_hole_verts)
    inner_radius = (hose_od + hose_tolerance) / 2.0
    outer_radius = inner_radius + tube_wall

    # Sample the port hole quad (inner surface of tube at base)
    inner_quad = _sample_quad_outline(
        port_hole_verts, port_hole_fillet, num_points,
    )
    # Outer surface at base = quad offset outward by tube_wall
    outer_quad = _offset_quad_outline(
        port_hole_verts, port_hole_fillet, tube_wall, num_points, centroid,
    )

    # Compute the start angle for circle sampling so that the first point
    # of the circle aligns angularly with the first point of the quad.
    first_quad_pt = inner_quad[0]
    start_angle = math.atan2(
        first_quad_pt[1] - centroid[1],
        first_quad_pt[0] - centroid[0],
    )

    # Sample the target circles
    inner_circle = _sample_circle(
        centroid[0], centroid[1], inner_radius, num_points, start_angle,
    )
    outer_circle = _sample_circle(
        centroid[0], centroid[1], outer_radius, num_points, start_angle,
    )

    # --- Build wires at each station ---
    outer_wires = []
    inner_wires = []
    for i in range(num_stations + 1):
        t = i / num_stations
        z = z_base + t * straight_length

        # Interpolate between quad and circle
        outer_pts = [
            (
                (1 - t) * oq[0] + t * oc[0],
                (1 - t) * oq[1] + t * oc[1],
            )
            for oq, oc in zip(outer_quad, outer_circle)
        ]
        inner_pts = [
            (
                (1 - t) * iq[0] + t * ic[0],
                (1 - t) * iq[1] + t * ic[1],
            )
            for iq, ic in zip(inner_quad, inner_circle)
        ]

        outer_wires.append(_make_wire_from_points(outer_pts, z))
        inner_wires.append(_make_wire_from_points(inner_pts, z))

    # --- Loft outer and inner shells ---
    outer_solid = cq.Solid.makeLoft(outer_wires)
    inner_solid = cq.Solid.makeLoft(inner_wires)

    # Hollow tube = outer - inner
    result = cq.Workplane("XY").add(outer_solid).cut(
        cq.Workplane("XY").add(inner_solid)
    )
    return result


# ---------------------------------------------------------------------------
# Elbow builder: 90° sweep of circular cross-section
# ---------------------------------------------------------------------------

def build_elbow(
    center_x: float,
    center_y: float,
    z_start: float,
    hose_od: float,
    hose_tolerance: float,
    tube_wall: float,
    bend_radius: float,
    bend_direction_deg: float = 0.0,
) -> cq.Workplane:
    """
    Build a 90° elbow that curves from +Z direction toward a configurable
    direction in the XY plane.

    bend_direction_deg: 0 = toward -X (A-D edge).  Positive rotates the
    exit direction toward -Y (A-B edge / downward).
    """
    inner_r = (hose_od + hose_tolerance) / 2.0
    outer_r = inner_r + tube_wall
    alpha = math.radians(bend_direction_deg)

    # Exit direction in the XY plane (rotated from -X toward -Y)
    exit_dir = (-math.cos(alpha), -math.sin(alpha), 0.0)

    # Build a custom plane for the arc path.
    # The plane contains +Z and the exit direction.
    # U-axis (workplane X) = exit_dir, V-axis (workplane Y) = +Z
    # Normal = U × V
    plane_normal = (-math.sin(alpha), math.cos(alpha), 0.0)
    bend_plane = cq.Plane(
        origin=cq.Vector(center_x, center_y, z_start),
        xDir=cq.Vector(*exit_dir),
        normal=cq.Vector(*plane_normal),
    )

    # 90° arc in the custom plane's 2D coords.
    # Arc goes from (0, 0) to (-R, R).  Midpoint at 45°.
    mid_u = -bend_radius + bend_radius * math.cos(math.pi / 4)
    mid_v = bend_radius * math.sin(math.pi / 4)

    path = (
        cq.Workplane(bend_plane)
        .moveTo(0, 0)
        .threePointArc((mid_u, mid_v), (-bend_radius, bend_radius))
    )

    # Annular cross-section perpendicular to path start (+Z direction → XY plane)
    profile = (
        cq.Workplane("XY", origin=(center_x, center_y, z_start))
        .circle(outer_r)
        .circle(inner_r)
    )

    return profile.sweep(path)


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
    # Use +Z as the xDir (perpendicular to exit_dir which is in XY plane).
    socket_plane = cq.Plane(
        origin=cq.Vector(exit_x, exit_y, exit_z),
        xDir=cq.Vector(0, 0, 1),
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
    straight_length: float = STRAIGHT_LENGTH,
    bend_radius: float = BEND_RADIUS,
    bend_direction_deg: float = BEND_DIRECTION_DEG,
    num_stations: int = NUM_LOFT_STATIONS,
    num_points: int = NUM_PROFILE_POINTS,
) -> cq.Workplane:
    """Build the adapter at the specified stage."""

    # Z coordinate of the top of the faceplate cap (in build orientation)
    z_cap_top = WALL_HEIGHT + CAP_THICKNESS

    # Port hole centroid — this is the tube centerline
    centroid = _quad_centroid(PORT_HOLE_VERTS)
    cx, cy = centroid

    # 1. Faceplate (no flip — we flip the whole assembly at the end)
    print("  Building faceplate...")
    result = build_faceplate(flip_for_print=False)

    # 2. Transition loft (quad → circle)
    print("  Building transition loft...")
    loft = build_transition_loft(
        port_hole_verts=PORT_HOLE_VERTS,
        port_hole_fillet=PORT_HOLE_FILLET,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        straight_length=straight_length,
        num_stations=num_stations,
        num_points=num_points,
        z_base=z_cap_top,
    )
    result = result.union(loft)

    if stage == "loft_test":
        return _orient_for_print(result)

    # 3. 90° elbow
    z_loft_top = z_cap_top + straight_length
    alpha = math.radians(bend_direction_deg)
    print("  Building 90° elbow...")
    elbow = build_elbow(
        center_x=cx,
        center_y=cy,
        z_start=z_loft_top,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        bend_radius=bend_radius,
        bend_direction_deg=bend_direction_deg,
    )
    result = result.union(elbow)

    if stage == "elbow_test":
        return _orient_for_print(result)

    # 4. Hose socket
    # Elbow exit point and direction (depends on bend_direction_deg)
    exit_dir = (-math.cos(alpha), -math.sin(alpha), 0.0)
    socket_x = cx + bend_radius * math.cos(alpha)
    socket_y = cy + bend_radius * math.sin(alpha)
    socket_z = z_loft_top + bend_radius
    print("  Building hose socket...")
    socket = build_socket(
        exit_x=socket_x,
        exit_y=socket_y,
        exit_z=socket_z,
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
    "loft_test": "Faceplate + straight transition loft (quad → circle)",
    "elbow_test": "Faceplate + loft + 90° elbow",
    "full": "Complete adapter: faceplate + loft + elbow + hose socket",
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
    parser.add_argument("--straight-length", type=float, default=STRAIGHT_LENGTH)
    parser.add_argument("--bend-radius", type=float, default=BEND_RADIUS)
    parser.add_argument("--bend-direction-deg", type=float, default=BEND_DIRECTION_DEG,
                        help="Bend direction (degrees). 0=toward A-D edge, positive=toward A-B.")
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
        straight_length=args.straight_length,
        bend_radius=args.bend_radius,
        bend_direction_deg=args.bend_direction_deg,
        num_stations=args.num_stations,
        num_points=args.num_points,
    )

    name = f"dust_port_adapter_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)
    print(f"Done → {Path(args.output_dir) / (name + '.stl')}")


if __name__ == "__main__":
    main()
