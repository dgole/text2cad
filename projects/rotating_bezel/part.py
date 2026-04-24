#!/usr/bin/env python3
"""
Rotating Bezel — Magnetic detent ring pair (edge-slot design)

Description:
    Two stacked rings with evenly-spaced magnet slots cut into the
    outer rim. Each slot is a rectangular tunnel open only on the
    outer edge — magnets slide in radially and are enclosed by a
    floor and ceiling (1mm each). When the rings are stacked, magnets
    attract through ~2mm of plastic (1mm per ring).

    Both rings are identical geometry — flip one upside-down so the
    interface faces meet and magnets align.

Usage:
    python part.py ring                 # Plain ring (no text)
    python part.py bezel                # Ring with engraved 1-12 digits
    python part.py pair                 # Both rings side-by-side
    python part.py ring --num-magnets 8 # Override magnet count
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from pathlib import Path

# Add repo root to path so we can import cad.*
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

import cadquery as cq  # noqa: E402
from cad.export import to_stl  # noqa: E402

# ---------------------------------------------------------------------------
# Load config — single source of truth for all parts in this project
# ---------------------------------------------------------------------------

_CONFIG_PATH = Path(__file__).parent / "config.json"
with open(_CONFIG_PATH) as _f:
    CFG = json.load(_f)

OUTPUT_DIR = Path(__file__).parent / "output"

# ---------------------------------------------------------------------------
# Parameters from config — all dimensions in mm.
# ---------------------------------------------------------------------------

MAGNET_DIAMETER = CFG["magnet_diameter"]
MAGNET_HEIGHT = CFG["magnet_height"]
MAGNET_CLEARANCE = CFG["magnet_clearance"]
NUM_MAGNETS = CFG["num_magnets"]

RING_OD = CFG["ring_od"]
RING_ID = CFG["ring_id"]
RING_HEIGHT = CFG["ring_height"]
MAGNET_FLOOR = CFG["magnet_floor"]
SLOT_DEPTH = CFG["slot_depth"]

BEZEL_EXTRA_HEIGHT = CFG["bezel_extra_height"]
TEXT_FONT_SIZE = CFG["text_font_size"]
TEXT_ENGRAVE_DEPTH = CFG["text_engrave_depth"]


# ---------------------------------------------------------------------------
# Build stages
# ---------------------------------------------------------------------------

def build_ring(
    ring_od: float = RING_OD,
    ring_id: float = RING_ID,
    ring_height: float = RING_HEIGHT,
    magnet_floor: float = MAGNET_FLOOR,
    magnet_diameter: float = MAGNET_DIAMETER,
    magnet_height: float = MAGNET_HEIGHT,
    magnet_clearance: float = MAGNET_CLEARANCE,
    num_magnets: int = NUM_MAGNETS,
    slot_depth: float = SLOT_DEPTH,
    **_kw,
) -> cq.Workplane:
    """
    Single ring with edge-slot magnet pockets.

    Slots are rectangular tunnels cut radially inward from the outer
    rim.  Each slot is enclosed top and bottom by magnet_floor walls.
    The magnet (axis vertical) slides in from the outside edge.

    Print with either face down — no supports needed since slots are
    enclosed (bridging over 5mm width at 1mm ceiling is fine for FDM).
    """
    outer_r = ring_od / 2
    inner_r = ring_id / 2

    # Slot dimensions
    slot_w = magnet_diameter + magnet_clearance   # tangential (circumferential)
    slot_h = magnet_height                        # Z — snug fit, clamped by floor/ceiling
    slot_d = slot_depth                           # radial depth into the wall
    overshoot = 1.0                               # extend cutter past outer rim

    # Radial extents of the cutter box
    cutter_inner_r = outer_r - slot_d             # inner wall of slot
    cutter_outer_r = outer_r + overshoot          # past the rim
    cutter_radial_size = cutter_outer_r - cutter_inner_r
    cutter_center_r = (cutter_inner_r + cutter_outer_r) / 2

    # Z position — slot centered vertically in the ring
    slot_z_center = magnet_floor + slot_h / 2

    # --- Annular ring body ---
    body = (
        cq.Workplane("XY")
        .circle(outer_r)
        .circle(inner_r)
        .extrude(ring_height)
    )

    # --- Cut magnet slots from the outer rim ---
    for i in range(num_magnets):
        angle_deg = 360.0 * i / num_magnets

        cutter = (
            cq.Workplane("XY")
            .box(cutter_radial_size, slot_w, slot_h,
                 centered=(True, True, True))
            .translate((cutter_center_r, 0, slot_z_center))
            .rotate((0, 0, 0), (0, 0, 1), angle_deg)
        )
        body = body.cut(cutter)

    return body


def build_pair(
    ring_od: float = RING_OD,
    ring_id: float = RING_ID,
    ring_height: float = RING_HEIGHT,
    magnet_floor: float = MAGNET_FLOOR,
    magnet_diameter: float = MAGNET_DIAMETER,
    magnet_height: float = MAGNET_HEIGHT,
    magnet_clearance: float = MAGNET_CLEARANCE,
    num_magnets: int = NUM_MAGNETS,
    slot_depth: float = SLOT_DEPTH,
    **_kw,
) -> cq.Workplane:
    """
    Both rings placed side-by-side for a single print.

    Ring A on the left, Ring B on the right, separated by a gap.
    """
    kw = dict(
        ring_od=ring_od, ring_id=ring_id, ring_height=ring_height,
        magnet_floor=magnet_floor, magnet_diameter=magnet_diameter,
        magnet_height=magnet_height, magnet_clearance=magnet_clearance,
        num_magnets=num_magnets, slot_depth=slot_depth,
    )

    gap = 5.0  # mm between the two rings on the build plate
    offset_x = ring_od / 2 + gap / 2

    ring_a = build_ring(**kw).translate((-offset_x, 0, 0))
    ring_b = build_ring(**kw).translate((offset_x, 0, 0))

    return ring_a.union(ring_b)


def build_bezel(
    ring_od: float = RING_OD,
    ring_id: float = RING_ID,
    ring_height: float = RING_HEIGHT,
    magnet_floor: float = MAGNET_FLOOR,
    magnet_diameter: float = MAGNET_DIAMETER,
    magnet_height: float = MAGNET_HEIGHT,
    magnet_clearance: float = MAGNET_CLEARANCE,
    num_magnets: int = NUM_MAGNETS,
    slot_depth: float = SLOT_DEPTH,
    bezel_extra_height: float = BEZEL_EXTRA_HEIGHT,
    text_font_size: float = TEXT_FONT_SIZE,
    text_engrave_depth: float = TEXT_ENGRAVE_DEPTH,
    **_kw,
) -> cq.Workplane:
    """
    Ring with 12-hour digits engraved on the top face.

    The ring is taller than the plain version — extra material is added
    above the magnet ceiling to provide a face for the engraved text.
    Digits 1-12 are arranged in clock positions at 30-degree intervals.
    """
    total_height = ring_height + bezel_extra_height

    # Build the base ring at the taller height
    body = build_ring(
        ring_od=ring_od, ring_id=ring_id, ring_height=total_height,
        magnet_floor=magnet_floor, magnet_diameter=magnet_diameter,
        magnet_height=magnet_height, magnet_clearance=magnet_clearance,
        num_magnets=num_magnets, slot_depth=slot_depth,
    )

    # Text radius — centered on the ring face
    r_text = (ring_od / 2 + ring_id / 2) / 2

    # Engrave digits 1-12 on the top face
    for n in range(1, 13):
        digit = str(n)
        # Clock angle: 12 at top (+Y), going clockwise
        clock_deg = -(n % 12) * 30  # rotation from 12-o'clock

        # Create text solid at origin on XY plane
        # text() extrudes in +Z from the workplane
        txt = (
            cq.Workplane("XY")
            .text(digit, text_font_size, text_engrave_depth,
                  cut=False, combine=True, font="Arial")
        )

        # Position: put text at 12-o'clock (0, r_text), then rotate
        # to final clock position. Text reads left-to-right at each
        # position, with tops of digits pointing outward from center.
        txt = (
            txt
            .translate((0, r_text, total_height - text_engrave_depth))
            .rotate((0, 0, 0), (0, 0, 1), clock_deg)
        )

        body = body.cut(txt)

    return body


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "ring": build_ring,
    "bezel": build_bezel,
    "pair": build_pair,
}


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("stage", choices=list(STAGES.keys()),
                        help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(OUTPUT_DIR))

    # Ring geometry overrides
    parser.add_argument("--ring-od", type=float, default=RING_OD,
                        help="Ring outer diameter")
    parser.add_argument("--ring-id", type=float, default=RING_ID,
                        help="Ring inner diameter (bore)")
    parser.add_argument("--ring-height", type=float, default=RING_HEIGHT,
                        help="Ring height (floor + magnet + ceiling)")

    # Magnet overrides
    parser.add_argument("--magnet-diameter", type=float, default=MAGNET_DIAMETER,
                        help="Magnet diameter")
    parser.add_argument("--magnet-height", type=float, default=MAGNET_HEIGHT,
                        help="Magnet height")
    parser.add_argument("--magnet-clearance", type=float, default=MAGNET_CLEARANCE,
                        help="Extra slot width for fit")
    parser.add_argument("--num-magnets", type=int, default=NUM_MAGNETS,
                        help="Number of magnet positions")
    parser.add_argument("--slot-depth", type=float, default=SLOT_DEPTH,
                        help="Radial depth of magnet slot into wall")

    args = parser.parse_args()

    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}
    kw["magnet_floor"] = MAGNET_FLOOR

    body = STAGES[args.stage](**kw)

    name = f"rotating_bezel_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
