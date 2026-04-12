"""
Common CAD operations — thin wrappers that keep part scripts readable.
"""

from __future__ import annotations

from typing import Tuple

import cadquery as cq


def extrude(workplane: cq.Workplane, height: float) -> cq.Workplane:
    """Extrude a pending 2D profile into a solid."""
    return workplane.extrude(height)


def add_screw_hole(
    body: cq.Workplane,
    diameter: float,
    position: Tuple[float, float],
    face_selector: str = ">Z",
) -> cq.Workplane:
    """
    Cut a through-hole at (x, y) on the selected face.
    Defaults to the top face (>Z).
    """
    return (
        body
        .faces(face_selector)
        .workplane()
        .pushPoints([position])
        .hole(diameter)
    )


def add_lip(
    body: cq.Workplane,
    width: float,
    height: float,
    lip_depth: float,
    lip_thickness: float,
    fillet: float = 0.0,
) -> cq.Workplane:
    """
    Add an inward-facing clip lip around a rectangular opening on the top face.
    The lip is a thin ring that overhangs inward, meant to grab onto a rim.
    """
    # Outer shell matches the opening; inner shell is the opening minus lip
    outer = (
        cq.Workplane("XY")
        .rect(width, height)
    )
    inner_w = width - 2 * lip_thickness
    inner_h = height - 2 * lip_thickness
    inner = (
        cq.Workplane("XY")
        .rect(inner_w, inner_h)
    )
    lip = outer.extrude(lip_depth).cut(inner.extrude(lip_depth))

    # Position the lip on top of the existing body
    top_z = body.val().BoundingBox().zmax
    lip = lip.translate((0, 0, top_z))
    return body.union(lip)
