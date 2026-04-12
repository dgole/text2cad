"""
Export utilities — write cadquery solids to STL files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Union

import cadquery as cq

DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parent.parent / "output"


def to_stl(
    body: cq.Workplane,
    name: str,
    output_dir: Optional[Union[str, Path]] = None,
    tolerance: float = 0.01,
    angular_tolerance: float = 0.1,
) -> Path:
    """
    Export a cadquery solid to an STL file.

    Returns the path to the written file.
    """
    out = Path(output_dir) if output_dir else DEFAULT_OUTPUT_DIR
    out.mkdir(parents=True, exist_ok=True)

    if not name.endswith(".stl"):
        name += ".stl"

    filepath = out / name
    cq.exporters.export(
        body,
        str(filepath),
        exportType="STL",
        tolerance=tolerance,
        angularTolerance=angular_tolerance,
    )
    print(f"Exported: {filepath}  ({os.path.getsize(filepath) / 1024:.1f} KB)")
    return filepath
