#!/usr/bin/env python3
"""
Build every stage of every project.

This is the regression check for shared-code changes. Anything in `cad/` is
imported by every project, so a change there can silently break geometry in a
project you weren't thinking about. Run this before and after such a change.

Usage:
    python build.py                  # rebuild everything into each project's output/
    python build.py desk_organizer   # limit to one project (repeatable)
    python build.py --snapshot       # record current geometry as the baseline
    python build.py --check          # rebuild to a temp dir, compare to baseline

`--check` compares geometric invariants (triangle count, volume, surface area,
bounding box) rather than raw file bytes, so it stays meaningful across
cadquery/OCCT upgrades. A byte-identical export is reported as `identical`;
one that differs in bytes but matches geometrically is reported as `equal`.
"""

from __future__ import annotations

import argparse
import ast
import concurrent.futures
import hashlib
import json
import shutil
import struct
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO_ROOT = Path(__file__).resolve().parent
PROJECTS_DIR = REPO_ROOT / "projects"
BASELINE_PATH = REPO_ROOT / "build_baseline.json"

# Relative tolerance for volume/area/bbox comparison. Tessellation is
# deterministic today, so this only absorbs floating-point noise.
TOLERANCE = 1e-6


# ---------------------------------------------------------------------------
# Discovery
# ---------------------------------------------------------------------------

def stages_of(script: Path) -> List[Optional[str]]:
    """
    Read a script's STAGES registry without importing it.

    Importing would execute the module (config load, sys.path mutation, sibling
    imports), so we parse instead. Returns [None] for scripts with no registry,
    meaning "invoke with no stage argument".
    """
    tree = ast.parse(script.read_text())
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if any(getattr(t, "id", None) == "STAGES" for t in node.targets):
            if isinstance(node.value, ast.Dict):
                return [k.value for k in node.value.keys if isinstance(k, ast.Constant)]
    return [None]


def discover(only: List[str]) -> List[Tuple[Path, Optional[str]]]:
    """Every (script, stage) pair in the repo, optionally filtered by project."""
    jobs = []
    for script in sorted(PROJECTS_DIR.glob("*/*.py")):
        if only and script.parent.name not in only:
            continue
        for stage in stages_of(script):
            jobs.append((script, stage))
    return jobs


# ---------------------------------------------------------------------------
# Geometry measurement
# ---------------------------------------------------------------------------

def measure(stl: Path) -> Dict[str, object]:
    """
    Extract geometric invariants from a binary STL.

    Volume is the signed-tetrahedron sum over all triangles, which is exact for
    a closed mesh and independent of triangle ordering.
    """
    data = stl.read_bytes()
    count = struct.unpack("<I", data[80:84])[0]

    volume = 0.0
    area = 0.0
    lo = [float("inf")] * 3
    hi = [float("-inf")] * 3

    for i in range(count):
        base = 84 + i * 50
        # 12 floats: normal (skipped), then three vertices
        vals = struct.unpack("<12f", data[base:base + 48])
        ax, ay, az = vals[3:6]
        bx, by, bz = vals[6:9]
        cx, cy, cz = vals[9:12]

        # Signed volume of the tetrahedron (origin, a, b, c)
        volume += (
            ax * (by * cz - bz * cy)
            - ay * (bx * cz - bz * cx)
            + az * (bx * cy - by * cx)
        ) / 6.0

        # Triangle area via half the cross-product magnitude
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        area += 0.5 * (nx * nx + ny * ny + nz * nz) ** 0.5

        for axis, vertex in enumerate(((ax, bx, cx), (ay, by, cy), (az, bz, cz))):
            lo[axis] = min(lo[axis], *vertex)
            hi[axis] = max(hi[axis], *vertex)

    return {
        "triangles": count,
        "volume": abs(volume),
        "area": area,
        # Absolute corners, not extents — a part that drifts off the build
        # plate has the same size but is no longer printable, and that must
        # register as a change.
        "bbox_min": lo,
        "bbox_max": hi,
        # Informational only — changes on any OCCT upgrade even when the
        # geometry is unchanged, so --check never fails on this alone.
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def compare(old: Dict, new: Dict) -> Optional[str]:
    """Return a human-readable description of the first difference, or None."""
    if old["triangles"] != new["triangles"]:
        return f"triangles {old['triangles']} -> {new['triangles']}"
    for key in ("volume", "area"):
        a, b = old[key], new[key]
        if abs(a - b) > TOLERANCE * max(abs(a), abs(b), 1.0):
            return f"{key} {a:.6f} -> {b:.6f}"
    for corner in ("bbox_min", "bbox_max"):
        for axis, (a, b) in enumerate(zip(old[corner], new[corner])):
            if abs(a - b) > TOLERANCE * max(abs(a), abs(b), 1.0):
                return f"{corner}[{'xyz'[axis]}] {a:.6f} -> {b:.6f}"
    return None


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------

def build(script: Path, stage: Optional[str], out_dir: Path) -> Tuple[bool, str, List[Path]]:
    """
    Run one script stage, writing STLs to out_dir.

    Returns (ok, message, stl_paths). We collect whatever STLs appear rather
    than predicting filenames, so this keeps working regardless of how a script
    names its output.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    cmd = [sys.executable, str(script)] + ([stage] if stage else []) + ["-o", str(out_dir)]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(REPO_ROOT))
    if proc.returncode != 0:
        tail = (proc.stderr.strip().splitlines() or ["(no stderr)"])[-1]
        return False, tail, []
    return True, "", sorted(out_dir.glob("*.stl"))


def job_key(script: Path, stage: Optional[str]) -> str:
    rel = script.relative_to(REPO_ROOT)
    return f"{rel}::{stage}" if stage else str(rel)


def run_all(jobs, out_root: Optional[Path]):
    """
    Build every job, in parallel.

    When out_root is set each job gets an isolated subdirectory (used by
    --check/--snapshot so measurements can't be confused by stale files).
    Otherwise output goes to each project's own output/ dir.
    """
    def one(job):
        script, stage = job
        key = job_key(script, stage)
        if out_root is not None:
            dest = out_root / key.replace("/", "_").replace("::", "_")
        else:
            dest = script.parent / "output"
        ok, msg, stls = build(script, stage, dest)
        return key, ok, msg, stls

    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
        return list(pool.map(one, jobs))


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("projects", nargs="*", help="Limit to these project names.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--snapshot", action="store_true",
                      help="Record current geometry as the baseline.")
    mode.add_argument("--check", action="store_true",
                      help="Compare current geometry against the baseline.")
    args = parser.parse_args()

    jobs = discover(args.projects)
    if not jobs:
        print("No matching projects.")
        return 1

    scratch = Path(tempfile.mkdtemp(prefix="text2cad-build-")) if (args.check or args.snapshot) else None
    try:
        results = run_all(jobs, scratch)

        failures = [(k, m) for k, ok, m, _ in results if not ok]
        for key, ok, msg, _ in results:
            if not ok:
                print(f"FAIL  {key}\n      {msg}")

        if failures:
            print(f"\n{len(failures)} of {len(jobs)} stages failed to build.")
            return 1

        if not (args.check or args.snapshot):
            print(f"Built {len(jobs)} stages across "
                  f"{len({k.split('/')[1] for k, *_ in results})} projects.")
            return 0

        # Measure everything that was produced
        current: Dict[str, Dict] = {}
        for key, _ok, _msg, stls in results:
            for stl in stls:
                current[f"{key}#{stl.name}"] = measure(stl)

        # A project filter means we only built part of the repo, so the rest of
        # the baseline is out of scope — it must be neither compared against
        # nor dropped on snapshot.
        built_jobs = {job_key(s, st) for s, st in jobs}
        in_scope = lambda name: name.rsplit("#", 1)[0] in built_jobs  # noqa: E731

        if args.snapshot:
            merged = {}
            if args.projects and BASELINE_PATH.exists():
                merged = {k: v for k, v in json.loads(BASELINE_PATH.read_text()).items()
                          if not in_scope(k)}
            merged.update(current)
            BASELINE_PATH.write_text(json.dumps(merged, indent=2, sort_keys=True) + "\n")
            print(f"Baseline written: {BASELINE_PATH.name} "
                  f"({len(current)} parts recorded, {len(merged)} total)")
            return 0

        if not BASELINE_PATH.exists():
            print(f"No baseline at {BASELINE_PATH.name}. Run: python build.py --snapshot")
            return 1

        baseline = {k: v for k, v in json.loads(BASELINE_PATH.read_text()).items()
                    if in_scope(k)}
        changed, identical, equal = [], 0, 0
        for name in sorted(set(baseline) | set(current)):
            if name not in baseline:
                changed.append(f"NEW      {name}")
            elif name not in current:
                changed.append(f"MISSING  {name}")
            else:
                diff = compare(baseline[name], current[name])
                if diff:
                    changed.append(f"CHANGED  {name}\n         {diff}")
                elif baseline[name]["sha256"] == current[name]["sha256"]:
                    identical += 1
                else:
                    equal += 1

        for line in changed:
            print(line)

        summary = f"{identical} identical"
        if equal:
            summary += f", {equal} geometrically equal"
        if changed:
            print(f"\n{len(changed)} changed, {summary}.")
            return 1
        print(f"All {len(current)} parts unchanged ({summary}).")
        return 0
    finally:
        if scratch:
            shutil.rmtree(scratch, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
