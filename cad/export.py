"""
Export utilities — write cadquery solids to STL files.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Union

import cadquery as cq


def to_stl(
    body: cq.Workplane,
    name: str,
    output_dir: Union[str, Path],
    tolerance: float = 0.01,
    angular_tolerance: float = 0.1,
) -> Path:
    """
    Export a cadquery solid to an STL file.

    output_dir is required — it previously defaulted to a repo-root `output/`
    that does not exist, so a caller that forgot it would silently create a
    stray directory instead of writing next to its project.

    Returns the path to the written file.
    """
    out = Path(output_dir)
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
