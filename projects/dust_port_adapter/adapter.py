#!/usr/bin/env python3
"""
Dust Port Adapter — complete adapter with angled transition tube.

Builds the full adapter: faceplate (clips onto the saw's dust port rim)
and a straight angled transition tube that morphs from the irregular port
hole to a circular hose connection while going at ~45° from vertical.

Stages:
    transition_test — faceplate + angled transition (quad → circle)
    full            — faceplate + angled transition + female hose socket

Usage:
    python adapter.py full
    python adapter.py transition_test
    python adapter.py full --exit-angle-deg 60 --tube-length 40
"""

from __future__ import annotations

import math
import sys
from functools import partial
from pathlib import Path
from typing import List, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.cli import load_config, run  # noqa: E402
from cad.geometry import on_build_plate  # noqa: E402

# Import builders from sibling modules
from faceplate import build_faceplate  # noqa: E402
from profile_test import _fillet_corner  # noqa: E402

# ---------------------------------------------------------------------------
# Load config
# ---------------------------------------------------------------------------

CFG = load_config(__file__)

# ---------------------------------------------------------------------------
# Parameters from config
# ---------------------------------------------------------------------------

# Faceplate dimensions (needed for positioning the tube)
WALL_HEIGHT = CFG["faceplate"]["wall_height"]
CAP_THICKNESS = CFG["faceplate"]["cap_thickness"]
SCREW_X = CFG["faceplate"]["screw_x"]
SCREW_Y = CFG["faceplate"]["screw_y"]
SCREW_ACCESS_DIAMETER = CFG["faceplate"]["screw_access_diameter"]

# Port hole shape (the quad cutout in the cap — tube starts here)
_ph = CFG["faceplate"]["port_hole"]
PORT_HOLE_VERTS = [tuple(_ph[k]) for k in ("A", "B", "C", "D")]
PORT_HOLE_FILLETS = [_ph["fillets"][k] for k in ("A", "B", "C", "D")]

# Transition tube parameters
_tr = CFG["transition"]
HOSE_OD = _tr["hose_od"]
HOSE_TOLERANCE = _tr["hose_tolerance"]
SOCKET_DEPTH = _tr["socket_depth"]
TUBE_WALL = _tr["tube_wall"]
TUBE_WALL_BASE = _tr["tube_wall_base"]
TUBE_LENGTH = _tr["tube_length"]
EXIT_ANGLE_DEG = _tr["exit_angle_deg"]
PATH_ANGLE_DEG = _tr["path_angle_deg"]
EXIT_DIRECTION_DEG = _tr["exit_direction_deg"]
TILT_BLEND_START = _tr["tilt_blend_start"]
PATH_BEND_START = _tr["path_bend_start"]
MORPH_EASE_EXP = _tr["morph_ease_exp"]
NUM_LOFT_STATIONS = _tr["num_loft_stations"]
NUM_PROFILE_POINTS = _tr["num_profile_points"]


# ---------------------------------------------------------------------------
# Geometry helpers
# ---------------------------------------------------------------------------

def _sample_quad_outline(
    verts: List[Tuple[float, float]],
    fillets: List[float],
    num_points: int,
) -> List[Tuple[float, float]]:
    """
    Sample `num_points` evenly-spaced (by arc length) around a filleted
    quadrilateral defined by `verts` with per-corner fillet radii.

    Returns a list of (x, y) points walking CCW around the shape.
    """
    n = len(verts)

    # --- Build a dense polyline of the outline (corners + fillets) ---
    segments = []  # each segment is a list of (x, y) points
    for i in range(n):
        p_prev = verts[(i - 1) % n]
        p_curr = verts[i]
        p_next = verts[(i + 1) % n]

        fillet_r = fillets[i]
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
            # target_len fell in the loop-closing gap (past the last recorded
            # point).  Extrapolating along the last recorded segment (frac > 1)
            # is only correct because the outline's final points are the
            # straight-edge samples leading back to outline[0] — collinear
            # with the closing gap.
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


def _offset_outline(
    sampled: List[Tuple[float, float]],
    offset: float,
    centroid: Tuple[float, float],
) -> List[Tuple[float, float]]:
    """
    Offset a sampled closed outline outward (positive offset) or inward
    (negative).

    Each sampled point moves along the local outline normal, so the offset
    is the true perpendicular wall thickness everywhere.  (Pushing points
    radially away from the centroid instead thins the wall wherever the
    outline runs obliquely to the radial direction — for the port hole quad
    that meant ~0.7mm of an intended 3mm wall near corner A.)

    The centroid is only used to orient the normal outward.
    """
    cx, cy = centroid
    n = len(sampled)
    result = []
    for i, (px, py) in enumerate(sampled):
        # Tangent from neighboring samples (central difference)
        p_prev = sampled[(i - 1) % n]
        p_next = sampled[(i + 1) % n]
        tx = p_next[0] - p_prev[0]
        ty = p_next[1] - p_prev[1]
        t_len = math.sqrt(tx * tx + ty * ty)
        if t_len < 1e-9:
            # Degenerate tangent; fall back to the radial direction
            nx, ny = px - cx, py - cy
            n_len = math.sqrt(nx * nx + ny * ny)
            if n_len < 1e-9:
                result.append((px, py))
                continue
            nx, ny = nx / n_len, ny / n_len
        else:
            nx, ny = ty / t_len, -tx / t_len
            # Orient outward (away from the centroid)
            if nx * (px - cx) + ny * (py - cy) < 0:
                nx, ny = -nx, -ny
        result.append((px + nx * offset, py + ny * offset))
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


def build_angled_transition(
    port_hole_verts: List[Tuple[float, float]],
    port_hole_fillets: List[float],
    hose_od: float,
    hose_tolerance: float,
    tube_wall: float,
    tube_wall_base: float,
    tube_length: float,
    exit_angle_deg: float,
    path_angle_deg: float,
    exit_direction_deg: float,
    tilt_blend_start: float,
    path_bend_start: float,
    morph_ease_exp: float,
    num_stations: int,
    num_points: int,
    z_base: float,
) -> Tuple[cq.Workplane, Tuple[float, float, float], Tuple[float, float, float]]:
    """
    Build a straight angled transition from port hole quad to hose circle.

    The tube goes in a straight line at exit_angle from vertical.  Cross-sections
    gradually tilt from flat (flush with the faceplate cap at the base) to
    perpendicular to the path at the exit.  The shape morphs from quad to circle.

    First wire is flat in XY → connects flush to the faceplate, no gap.

    Returns:
        (solid, exit_point, exit_direction)
    """
    centroid = _quad_centroid(port_hole_verts)
    cx, cy = centroid
    inner_radius = (hose_od + hose_tolerance) / 2.0

    exit_angle = math.radians(exit_angle_deg)
    path_angle = math.radians(path_angle_deg)
    alpha = math.radians(exit_direction_deg)

    # Horizontal direction the tube angles toward
    d_horiz = (-math.cos(alpha), -math.sin(alpha), 0.0)

    # Binormal: perpendicular to the tilt plane (for Rodrigues rotation)
    binormal = (-math.sin(alpha), math.cos(alpha), 0.0)

    # Sample the port hole quad (inner outline only — the outer surface is
    # derived per-station by offsetting the interpolated inner profile, so
    # the wall thickness is exact at every station and can taper).
    inner_quad = _sample_quad_outline(
        port_hole_verts, port_hole_fillets, num_points,
    )

    # Align circle sampling with first quad point
    first_quad_pt = inner_quad[0]
    circle_start = math.atan2(
        first_quad_pt[1] - cy,
        first_quad_pt[0] - cx,
    )
    inner_circle = _sample_circle(cx, cy, inner_radius, num_points, circle_start)

    def profiles_at(t: float) -> Tuple[List[Tuple[float, float]], List[Tuple[float, float]]]:
        """(inner, outer) 2D cross-section outlines at station t, pre-tilt."""
        # Shape morph: quad → circle, eased by 1-(1-t)**q so the big quad
        # shrinks toward the circle early, before the tilt picks up.
        # q=1 is a linear morph.
        s = 1.0 - (1.0 - t) ** morph_ease_exp
        inner_pts = [
            ((1 - s) * iq[0] + s * ic[0], (1 - s) * iq[1] + s * ic[1])
            for iq, ic in zip(inner_quad, inner_circle)
        ]
        # Wall thickness tapers from tube_wall_base at the faceplate to
        # tube_wall at the exit.  Near the base the tube's trailing surface
        # runs very oblique to the (near-flat) cross-sections, so an in-plane
        # wall of W yields a true perpendicular wall much thinner than W —
        # a thicker base wall compensates.
        wall_t = tube_wall_base + (tube_wall - tube_wall_base) * t
        return inner_pts, _offset_outline(inner_pts, wall_t, centroid)

    # --- Tilt schedule: keep the tube's underside straight ---
    # The underside (toward d_horiz, facing the faceplate) is the visually
    # dominant edge of the tube, and any fixed easing curve makes it bow
    # somewhere.  Instead, solve per station for the tilt that places the
    # underside surface point exactly on the straight chord from base to
    # exit.  That solution ends well short of exit_angle (which the exit
    # face must reach for the hose), so past `tilt_blend_start` the tilt
    # sweeps up to exit_angle with a slope-matched cubic that ends with zero
    # rotation rate — the unavoidable final sweep becomes one gentle bow
    # instead of a bulge, and the tube meets the socket without a kink.
    # --- Centerline: straight at path_angle, optionally bending to the exit
    # angle over the final stretch (past path_bend_start; 1.0 = no bend).
    # Without the bend the centerline still travels at path_angle when it
    # meets the socket (which runs at exit_angle), so the tube's underside
    # creases at the junction; a gentle arc arrives tangent to the socket.
    delta = exit_angle - path_angle
    bend_t = min(max(path_bend_start, 0.05), 1.0)

    def path_at(t: float) -> Tuple[float, float]:
        """Centerline point as (distance along d_horiz, height) from base."""
        if t <= bend_t or abs(delta) < 1e-9:
            return (t * tube_length * math.sin(path_angle),
                    t * tube_length * math.cos(path_angle))
        f = 1.0 - bend_t
        radius = f * tube_length / delta
        phi = path_angle + (t - bend_t) / f * delta
        return (
            bend_t * tube_length * math.sin(path_angle)
            + radius * (math.cos(path_angle) - math.cos(phi)),
            bend_t * tube_length * math.cos(path_angle)
            + radius * (math.sin(phi) - math.sin(path_angle)),
        )

    def rho_under(t: float) -> float:
        _, outer_pts = profiles_at(t)
        return max(
            (p[0] - cx) * d_horiz[0] + (p[1] - cy) * d_horiz[1]
            for p in outer_pts
        )

    def under_point(t: float, tilt: float) -> Tuple[float, float]:
        """Underside surface point in the (d_horiz, z) plane."""
        r = rho_under(t)
        pa, pz = path_at(t)
        return (pa + r * math.cos(tilt), pz - r * math.sin(tilt))

    chord_a = under_point(0.0, 0.0)
    chord_b = under_point(1.0, exit_angle)
    chord_dx = chord_b[0] - chord_a[0]
    chord_dy = chord_b[1] - chord_a[1]

    def solve_tilt(t: float) -> float:
        """Bisect for the tilt that puts the underside point on the chord."""
        lo, hi = 0.0, exit_angle
        for _ in range(40):
            mid = (lo + hi) / 2.0
            px, pz = under_point(t, mid)
            below = (px - chord_a[0]) * chord_dy - (pz - chord_a[1]) * chord_dx
            if below > 0:
                hi = mid
            else:
                lo = mid
        return (lo + hi) / 2.0

    t_star = min(max(tilt_blend_start, 0.05), 0.95)
    k0 = solve_tilt(t_star)
    m0 = (k0 - solve_tilt(t_star - 0.01)) / 0.01  # entry slope for the blend

    def tilt_at(t: float) -> float:
        if t <= t_star:
            return solve_tilt(t)
        s = (t - t_star) / (1.0 - t_star)
        h00 = 2 * s**3 - 3 * s**2 + 1
        h10 = s**3 - 2 * s**2 + s
        h01 = -2 * s**3 + 3 * s**2
        return h00 * k0 + h10 * (1.0 - t_star) * m0 + h01 * exit_angle

    # --- Build wires at each station ---
    outer_wires = []
    inner_wires = []
    for i in range(num_stations + 1):
        t = i / num_stations  # 0 at base, 1 at exit

        # Center position along the (possibly bent) centerline
        pa, pz = path_at(t)
        pos = (
            cx + pa * d_horiz[0],
            cy + pa * d_horiz[1],
            z_base + pz,
        )

        tilt = tilt_at(t)
        inner_pts_2d, outer_pts_2d = profiles_at(t)

        # Transform 2D → 3D: subtract centroid, rotate by -tilt, translate
        def transform(pts_2d: List[Tuple[float, float]]) -> List[Tuple[float, float, float]]:
            pts_3d = []
            for px, py in pts_2d:
                dx, dy = px - cx, py - cy
                rx, ry, rz = _rodrigues_rotate((dx, dy, 0.0), binormal, -tilt)
                pts_3d.append((pos[0] + rx, pos[1] + ry, pos[2] + rz))
            return pts_3d

        outer_wires.append(_make_wire_from_points_3d(transform(outer_pts_2d)))
        inner_wires.append(_make_wire_from_points_3d(transform(inner_pts_2d)))

    # --- Loft outer and inner shells ---
    outer_solid = cq.Solid.makeLoft(outer_wires)
    inner_solid = cq.Solid.makeLoft(inner_wires)

    # Hollow tube = outer - inner
    result = cq.Workplane("XY").add(outer_solid).cut(
        cq.Workplane("XY").add(inner_solid)
    ).solids()

    # --- Exit geometry ---
    exit_a, exit_z = path_at(1.0)
    exit_point = (
        cx + exit_a * d_horiz[0],
        cy + exit_a * d_horiz[1],
        z_base + exit_z,
    )

    final_face_normal = (
        math.sin(exit_angle) * d_horiz[0],
        math.sin(exit_angle) * d_horiz[1],
        math.cos(exit_angle),
    )

    return result, exit_point, final_face_normal


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
    tube_wall_base: float = TUBE_WALL_BASE,
    tube_length: float = TUBE_LENGTH,
    exit_angle_deg: float = EXIT_ANGLE_DEG,
    path_angle_deg: float = PATH_ANGLE_DEG,
    exit_direction_deg: float = EXIT_DIRECTION_DEG,
    tilt_blend_start: float = TILT_BLEND_START,
    path_bend_start: float = PATH_BEND_START,
    morph_ease_exp: float = MORPH_EASE_EXP,
    port_hole_ax: float = PORT_HOLE_VERTS[0][0], port_hole_ay: float = PORT_HOLE_VERTS[0][1],
    port_hole_bx: float = PORT_HOLE_VERTS[1][0], port_hole_by: float = PORT_HOLE_VERTS[1][1],
    port_hole_cx: float = PORT_HOLE_VERTS[2][0], port_hole_cy: float = PORT_HOLE_VERTS[2][1],
    port_hole_dx: float = PORT_HOLE_VERTS[3][0], port_hole_dy: float = PORT_HOLE_VERTS[3][1],
    port_hole_fillet_a: float = PORT_HOLE_FILLETS[0],
    port_hole_fillet_b: float = PORT_HOLE_FILLETS[1],
    port_hole_fillet_c: float = PORT_HOLE_FILLETS[2],
    port_hole_fillet_d: float = PORT_HOLE_FILLETS[3],
    screw_access_diameter: float = SCREW_ACCESS_DIAMETER,
    num_stations: int = NUM_LOFT_STATIONS,
    num_points: int = NUM_PROFILE_POINTS,
) -> cq.Workplane:
    """Build the adapter at the specified stage."""

    # Z coordinate of the top of the faceplate cap (in build orientation)
    z_cap_top = WALL_HEIGHT + CAP_THICKNESS

    port_hole_verts = [
        (port_hole_ax, port_hole_ay), (port_hole_bx, port_hole_by),
        (port_hole_cx, port_hole_cy), (port_hole_dx, port_hole_dy),
    ]
    port_hole_fillets = [
        port_hole_fillet_a, port_hole_fillet_b,
        port_hole_fillet_c, port_hole_fillet_d,
    ]

    # 1. Faceplate (no flip — we flip the whole assembly at the end).
    # The port hole outline is passed through so the cap cutout always
    # matches the tube's base cross-section.
    print("  Building faceplate...")
    result = build_faceplate(
        port_hole_ax=port_hole_ax, port_hole_ay=port_hole_ay,
        port_hole_bx=port_hole_bx, port_hole_by=port_hole_by,
        port_hole_cx=port_hole_cx, port_hole_cy=port_hole_cy,
        port_hole_dx=port_hole_dx, port_hole_dy=port_hole_dy,
        port_hole_fillet_a=port_hole_fillet_a,
        port_hole_fillet_b=port_hole_fillet_b,
        port_hole_fillet_c=port_hole_fillet_c,
        port_hole_fillet_d=port_hole_fillet_d,
        flip_for_print=False,
    )

    # 2. Angled transition (quad → circle, straight path)
    print("  Building angled transition...")
    transition, exit_point, exit_dir = build_angled_transition(
        port_hole_verts=port_hole_verts,
        port_hole_fillets=port_hole_fillets,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        tube_wall_base=tube_wall_base,
        tube_length=tube_length,
        exit_angle_deg=exit_angle_deg,
        path_angle_deg=path_angle_deg,
        exit_direction_deg=exit_direction_deg,
        tilt_blend_start=tilt_blend_start,
        path_bend_start=path_bend_start,
        morph_ease_exp=morph_ease_exp,
        num_stations=num_stations,
        num_points=num_points,
        z_base=z_cap_top - 1.0,  # overlap into cap for reliable boolean union
    )
    result = result.union(transition)

    # 2b. Screw access relief: the tube's flared wall base leans to within
    # ~2.8mm of the screw axis right where the screw head sits, so scoop a
    # vertical cylindrical pocket around the screw down to the cap.  Cuts
    # only the outer wall (the air channel stays ~7.6mm from the axis at the
    # pinch); starts 0.2mm below the cap top to spot-face a flat seat for
    # the head.  0 disables.
    if screw_access_diameter > 0:
        relief = (
            cq.Workplane("XY")
            .transformed(offset=(SCREW_X, SCREW_Y, z_cap_top - 0.2))
            .circle(screw_access_diameter / 2.0)
            .extrude(40)
        )
        result = result.cut(relief)

    if stage == "transition_test":
        return on_build_plate(result)

    # 3. Hose socket (extends from the transition exit)
    print("  Building hose socket...")
    
    # Overlap socket by 1mm into the tube to ensure solid union
    overlap_pt = (
        exit_point[0] - 1.0 * exit_dir[0],
        exit_point[1] - 1.0 * exit_dir[1],
        exit_point[2] - 1.0 * exit_dir[2],
    )

    socket = build_socket(
        exit_x=overlap_pt[0],
        exit_y=overlap_pt[1],
        exit_z=overlap_pt[2],
        exit_dir=exit_dir,
        hose_od=hose_od,
        hose_tolerance=hose_tolerance,
        tube_wall=tube_wall,
        socket_depth=socket_depth + 1.0,  # add 1mm to preserve usable depth
    )
    result = result.union(socket)

    return on_build_plate(result)


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

# build_adapter() takes the stage as an argument, so bind it per stage. The
# stage descriptions live in this module's docstring, which is the CLI help.
STAGES = {
    "transition_test": partial(build_adapter, stage="transition_test"),
    "full": partial(build_adapter, stage="full"),
}

PARAMS = {
    "hose_od": (HOSE_OD, "Hose outer diameter (mm)."),
    "hose_tolerance": HOSE_TOLERANCE,
    "socket_depth": SOCKET_DEPTH,
    "tube_wall": (TUBE_WALL, "Tube wall thickness at the hose exit (mm)."),
    "tube_wall_base": (TUBE_WALL_BASE,
                       "Tube wall thickness at the faceplate end (mm); tapers to tube_wall at the exit."),
    "tube_length": (TUBE_LENGTH, "Transition tube length along path (mm)."),
    "exit_angle_deg": (EXIT_ANGLE_DEG, "Angle of the tube exit from vertical (degrees)."),
    "path_angle_deg": (PATH_ANGLE_DEG, "Angle of travel from vertical (degrees)."),
    "exit_direction_deg": (EXIT_DIRECTION_DEG,
                           "Horizontal direction (degrees). 0=toward A-D, positive=toward A-B."),
    "tilt_blend_start": (TILT_BLEND_START,
                         "Fraction of the tube with a solved straight underside; the rest sweeps to exit_angle."),
    "path_bend_start": (PATH_BEND_START,
                        "Fraction of the tube with a straight centerline; the rest arcs to exit_angle so the "
                        "tube meets the socket tangent. 1.0 = no bend."),
    "morph_ease_exp": (MORPH_EASE_EXP,
                       "Quad->circle morph easing exponent (1-(1-t)**q). 1=linear; >1 shrinks the quad early."),
    "port_hole_ax": PORT_HOLE_VERTS[0][0], "port_hole_ay": PORT_HOLE_VERTS[0][1],
    "port_hole_bx": PORT_HOLE_VERTS[1][0], "port_hole_by": PORT_HOLE_VERTS[1][1],
    "port_hole_cx": PORT_HOLE_VERTS[2][0], "port_hole_cy": PORT_HOLE_VERTS[2][1],
    "port_hole_dx": PORT_HOLE_VERTS[3][0], "port_hole_dy": PORT_HOLE_VERTS[3][1],
    "port_hole_fillet_a": (PORT_HOLE_FILLETS[0], "Fillet radius at port hole corner A (acute)."),
    "port_hole_fillet_b": (PORT_HOLE_FILLETS[1], "Fillet radius at port hole corner B."),
    "port_hole_fillet_c": (PORT_HOLE_FILLETS[2], "Fillet radius at port hole corner C."),
    "port_hole_fillet_d": (PORT_HOLE_FILLETS[3], "Fillet radius at port hole corner D."),
    "screw_access_diameter": (SCREW_ACCESS_DIAMETER,
                              "Diameter of the cylindrical screw-access pocket cut into the tube wall. 0 = off."),
    "num_stations": (NUM_LOFT_STATIONS, "Number of intermediate cross-sections.", int),
    "num_points": (NUM_PROFILE_POINTS, "Points sampled around each cross-section.", int),
}


if __name__ == "__main__":
    run(__file__, STAGES, PARAMS)
