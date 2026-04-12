"""
Reusable 2D profile generators.

Each function returns a cadquery Workplane with a 2D wire/face on it,
ready to be extruded, swept, etc.
"""

import cadquery as cq


def rounded_rect(width: float, height: float, fillet: float = 0.0) -> cq.Workplane:
    """A centered rounded rectangle on the XY plane."""
    wp = cq.Workplane("XY").rect(width, height)
    if fillet > 0:
        wp = wp.val().fillet2D(fillet, wp.val().Vertices())
        wp = cq.Workplane("XY").add(wp).wires().toPending()
    return wp


def circle(diameter: float) -> cq.Workplane:
    """A centered circle on the XY plane."""
    return cq.Workplane("XY").circle(diameter / 2)


def rounded_rect_shell(
    outer_width: float,
    outer_height: float,
    wall: float,
    fillet: float = 0.0,
) -> cq.Workplane:
    """
    A hollow rounded rectangle (outer minus inner).
    Useful for clip rings / rims.
    """
    inner_w = outer_width - 2 * wall
    inner_h = outer_height - 2 * wall
    outer = rounded_rect(outer_width, outer_height, fillet)
    inner = rounded_rect(inner_w, inner_h, max(fillet - wall, 0))
    return outer.cut(inner)
