"""
Geometry helpers shared across projects.

Everything here was extracted from duplicated code in project scripts — this
module is deliberately small and grows only when a helper has proven itself in
more than one project. Speculative helpers rot unused; these did not.
"""

from __future__ import annotations

import cadquery as cq

# Fillets that exactly touch the limit of a face produce degenerate tangencies
# that OCCT often fails on. Back off by a hair.
_FILLET_EPSILON = 0.01


def safe_fillet_radius(radius: float, *spans: float) -> float:
    """
    Clamp a fillet radius to what the geometry can actually accept.

    A fillet can consume at most half of each dimension it has to fit within,
    so pass every constraining span. Returns a radius that may be <= 0, which
    callers should treat as "skip the fillet".

        safe_fillet_radius(5.0, width, depth)   # fits within both
    """
    return min(radius, *(span / 2 - _FILLET_EPSILON for span in spans))


def filleted_box(
    width: float,
    depth: float,
    height: float,
    fillet: float = 0.0,
) -> cq.Workplane:
    """
    Rectangular prism with filleted vertical edges, centered in XY with its
    base on Z=0. The fillet is clamped to fit and skipped if it degenerates.
    """
    body = cq.Workplane("XY").box(width, depth, height, centered=(True, True, False))
    radius = safe_fillet_radius(fillet, width, depth)
    if radius > _FILLET_EPSILON:
        body = body.edges("|Z").fillet(radius)
    return body


def on_build_plate(body: cq.Workplane) -> cq.Workplane:
    """
    Translate a body so its lowest point sits on Z=0, ready to print.

    A no-op when the body is already seated, so this is safe to apply
    unconditionally at the end of a build stage.
    """
    bb = body.val().BoundingBox()
    if abs(bb.zmin) > 0.001:
        body = body.translate((0, 0, -bb.zmin))
    return body
