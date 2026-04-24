#!/usr/bin/env python3
"""
Rotating Bezel — Magnetic detent ring pair

Description:
    Two stacked rings with evenly-spaced cylindrical magnet pockets.
    Magnets in each ring attract those in the other, creating snap-to
    detent positions. Rotate one ring to overcome magnetic force and
    click into the next position.

    Both rings are identical geometry — just flip one upside-down so
    the pocket openings face each other.

Usage:
    python part.py ring                 # Single ring
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _magnet_positions(num: int, ring_od: float, ring_id: float) -> list:
    """
    Return (x, y) positions for magnets evenly spaced around the ring.
    Magnets sit on the midline between inner and outer radius.
    """
    mid_r = (ring_od / 2 + ring_id / 2) / 2
    positions = []
    for i in range(num):
        angle = 2 * math.pi * i / num
        x = mid_r * math.cos(angle)
        y = mid_r * math.sin(angle)
        positions.append((x, y))
    return positions


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
    **_kw,
) -> cq.Workplane:
    """
    Single ring with magnet pockets.

    The ring sits with its base at Z=0. Magnet pockets open on the top
    face (Z = ring_height). Print with pockets facing up — no supports
    needed since pockets are simple cylindrical holes.
    """
    outer_r = ring_od / 2
    inner_r = ring_id / 2
    pocket_d = magnet_diameter + magnet_clearance
    pocket_depth = magnet_height  # pockets are exactly magnet height

    # --- Annular ring body ---
    body = (
        cq.Workplane("XY")
        .circle(outer_r)
        .circle(inner_r)
        .extrude(ring_height)
    )

    # --- Cut magnet pockets from the top face ---
    positions = _magnet_positions(num_magnets, ring_od, ring_id)
    for (px, py) in positions:
        pocket = (
            cq.Workplane("XY")
            .workplane(offset=ring_height)
            .center(px, py)
            .circle(pocket_d / 2)
            .extrude(-pocket_depth)
        )
        body = body.cut(pocket)

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
    **_kw,
) -> cq.Workplane:
    """
    Both rings placed side-by-side for a single print.

    Ring A on the left, Ring B on the right, separated by a gap.
    Both printed with pockets facing up.
    """
    kw = dict(
        ring_od=ring_od, ring_id=ring_id, ring_height=ring_height,
        magnet_floor=magnet_floor, magnet_diameter=magnet_diameter,
        magnet_height=magnet_height, magnet_clearance=magnet_clearance,
        num_magnets=num_magnets,
    )

    gap = 5.0  # mm between the two rings on the build plate
    offset_x = ring_od / 2 + gap / 2

    ring_a = build_ring(**kw).translate((-offset_x, 0, 0))
    ring_b = build_ring(**kw).translate((offset_x, 0, 0))

    return ring_a.union(ring_b)


# ---------------------------------------------------------------------------
# Stage registry
# ---------------------------------------------------------------------------

STAGES = {
    "ring": build_ring,
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
                        help="Ring height (floor + pocket)")

    # Magnet overrides
    parser.add_argument("--magnet-diameter", type=float, default=MAGNET_DIAMETER,
                        help="Magnet diameter")
    parser.add_argument("--magnet-height", type=float, default=MAGNET_HEIGHT,
                        help="Magnet height")
    parser.add_argument("--magnet-clearance", type=float, default=MAGNET_CLEARANCE,
                        help="Extra pocket diameter for fit")
    parser.add_argument("--num-magnets", type=int, default=NUM_MAGNETS,
                        help="Number of magnet positions")

    args = parser.parse_args()

    kw = {k.replace("-", "_"): v for k, v in vars(args).items()
          if k not in ("stage", "output_dir")}
    # Pass magnet_floor through from config (not a CLI flag for now)
    kw["magnet_floor"] = MAGNET_FLOOR

    body = STAGES[args.stage](**kw)

    name = f"rotating_bezel_{args.stage}"
    to_stl(body, name, output_dir=args.output_dir)


if __name__ == "__main__":
    main()
