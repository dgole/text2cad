"""
Dust port adapter for circular saw.

Design intent:
  1. A collar that clips onto the rectangular dust exhaust port rim
  2. Turns 90 degrees
  3. Connects to a dust collection hose
  4. Has a screw-through hole to anchor to the saw body

This module builds the part in stages so we can print test pieces
at each step:
  - test_plate:    flat plate matching the port outline (fit check)
  - test_collar:   plate + clip lip (snap-on fit check)
  - test_mounting: collar + screw arm (mounting check)
  - full_adapter:  everything + 90-degree elbow to hose
"""

import cadquery as cq

from cad.export import to_stl
from cad.ops import add_screw_hole

# ---------------------------------------------------------------------------
# Parameters — all dimensions in mm.  Tweak these after test prints.
# ---------------------------------------------------------------------------

# Dust port opening (inner rectangle the adapter mates to)
PORT_WIDTH = 42.0        # mm — wider dimension of port opening
PORT_HEIGHT = 28.0       # mm — shorter dimension
PORT_CORNER_RADIUS = 3.0 # mm — fillet on corners (0 = sharp)

# Rim / lip that the clip grabs onto
RIM_THICKNESS = 2.0      # mm — how far the rim sticks out from the port face
RIM_DEPTH = 3.0          # mm — how deep the rim extends (axially)

# Adapter wall
WALL = 2.5               # mm — wall thickness of the adapter body

# Plate (for test prints)
PLATE_THICKNESS = 3.0    # mm

# Screw hole
SCREW_HOLE_DIA = 4.5     # mm — clearance hole for #8 / M4 screw
SCREW_OFFSET_X = 0.0     # mm — lateral offset from port center
SCREW_OFFSET_Y = 30.0    # mm — distance above port center to screw hole

# Hose connection (for full adapter)
HOSE_INNER_DIA = 35.0    # mm — standard 1-3/8" shop vac hose
HOSE_LENGTH = 25.0       # mm — stub length to push hose onto


# ---------------------------------------------------------------------------
# Stage builders
# ---------------------------------------------------------------------------

def _base_rect(width: float, height: float, fillet: float) -> cq.Workplane:
    """Centered rounded rectangle on XY plane."""
    wp = cq.Workplane("XY").rect(width, height)
    if fillet > 0:
        wp = wp.extrude(0.01)  # need a solid to fillet
        wp = wp.edges("|Z").fillet(fillet)
        return wp
    return wp.extrude(0.01)


def test_plate(
    port_width: float = PORT_WIDTH,
    port_height: float = PORT_HEIGHT,
    corner_radius: float = PORT_CORNER_RADIUS,
    wall: float = WALL,
    thickness: float = PLATE_THICKNESS,
) -> cq.Workplane:
    """
    Flat plate matching the outer profile of the adapter collar.
    Print this first and hold it up to the port to check the outline.
    """
    outer_w = port_width + 2 * wall
    outer_h = port_height + 2 * wall
    outer_r = corner_radius + wall if corner_radius > 0 else 0

    plate = cq.Workplane("XY").rect(outer_w, outer_h)
    if outer_r > 0:
        plate = plate.extrude(thickness).edges("|Z").fillet(outer_r)
    else:
        plate = plate.extrude(thickness)

    # Cut out the inner port opening so you can see if it lines up
    cutout = cq.Workplane("XY").rect(port_width, port_height)
    if corner_radius > 0:
        cutout = cutout.extrude(thickness).edges("|Z").fillet(corner_radius)
    else:
        cutout = cutout.extrude(thickness)

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
    Plate + inward lip that clips over the port rim.
    The lip extends behind the plate (negative Z) to hook onto the rim.
    """
    plate = test_plate(port_width, port_height, corner_radius, wall, plate_thickness)

    # Lip: a ring that extends in -Z from the plate, fitting around the port rim
    lip_outer_w = port_width + 2 * rim_thickness
    lip_outer_h = port_height + 2 * rim_thickness
    lip_inner_w = port_width
    lip_inner_h = port_height

    lip_outer = cq.Workplane("XY").rect(lip_outer_w, lip_outer_h)
    lip_inner = cq.Workplane("XY").rect(lip_inner_w, lip_inner_h)

    if corner_radius > 0:
        lip_r_outer = corner_radius + rim_thickness
        lip_r_inner = corner_radius
        lip_solid = (
            lip_outer.extrude(-rim_depth).edges("|Z").fillet(lip_r_outer)
        ).cut(
            lip_inner.extrude(-rim_depth).edges("|Z").fillet(lip_r_inner)
        )
    else:
        lip_solid = lip_outer.extrude(-rim_depth).cut(lip_inner.extrude(-rim_depth))

    return plate.union(lip_solid)


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
    Collar + an arm extending to the screw hole location.
    """
    collar = test_collar(
        port_width, port_height, corner_radius, wall,
        plate_thickness, rim_thickness, rim_depth,
    )

    # Add a rectangular arm from the collar body to the screw location
    arm_width = screw_dia + 2 * wall
    outer_h = port_height + 2 * wall
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
# CLI entry point
# ---------------------------------------------------------------------------

def main():
    import argparse

    stages = {
        "plate": test_plate,
        "collar": test_collar,
        "mounting": test_mounting,
    }

    parser = argparse.ArgumentParser(
        description="Generate dust port adapter STL files."
    )
    parser.add_argument(
        "stage",
        choices=list(stages.keys()),
        help="Which build stage to export.",
    )
    parser.add_argument(
        "-o", "--output-dir",
        default=None,
        help="Output directory (default: ./output/)",
    )
    # Allow overriding key dimensions from CLI
    parser.add_argument("--port-width", type=float, default=PORT_WIDTH)
    parser.add_argument("--port-height", type=float, default=PORT_HEIGHT)
    parser.add_argument("--corner-radius", type=float, default=PORT_CORNER_RADIUS)
    parser.add_argument("--wall", type=float, default=WALL)
    parser.add_argument("--plate-thickness", type=float, default=PLATE_THICKNESS)

    args = parser.parse_args()

    kwargs = dict(
        port_width=args.port_width,
        port_height=args.port_height,
        corner_radius=args.corner_radius,
        wall=args.wall,
    )
    if args.stage != "plate":
        pass  # collar/mounting accept extra kwargs via defaults

    builder = stages[args.stage]
    body = builder(**{k: v for k, v in kwargs.items() if k in builder.__code__.co_varnames})

    name = f"dust_port_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
