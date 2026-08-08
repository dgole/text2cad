"""
Shared command-line runner for project scripts.

Every part script does the same four things: load config.json, build argparse
flags for the dimensions worth overriding, dispatch to a stage builder, and
export the result under a predictable name. Doing that by hand ten times let
the scripts drift into three incompatible dialects, so it lives here instead.

A script's main() becomes:

    from cad.cli import load_config, run

    STAGES = {"block": build_block, "full": build_full}

    if __name__ == "__main__":
        run(__file__, STAGES, params={
            "width": (BODY_WIDTH, "Overall body width (X)"),
            "count": (SLOT_COUNT, "Number of slots", int),
        })
"""

from __future__ import annotations

import argparse
import inspect
import json
from pathlib import Path
from typing import Callable, Dict, Mapping, Optional, Sequence, Union

import cadquery as cq

from cad.export import to_stl


def load_config(script: Union[str, Path]) -> dict:
    """Load the config.json sitting next to a project script."""
    return json.loads((Path(script).resolve().parent / "config.json").read_text())


def _spec(value) -> tuple:
    """
    Normalise a params entry into (default, help, type).

    Accepted forms:
        default
        (default, help)
        (default, help, type)

    Numbers default to `float` even when the config stores them as an int —
    dimensions are routinely written as `60` in config.json but must still
    accept `--width 60.5`. Counts must therefore ask for `int` explicitly.
    """
    if isinstance(value, tuple):
        if len(value) == 3:
            return value
        default, help_text = value
    else:
        default, help_text = value, None

    if isinstance(default, bool):
        raise TypeError("boolean parameters are not supported; use a flag instead")
    kind = float if isinstance(default, (int, float)) else type(default)
    return default, help_text, kind


def _accepted_kwargs(builder: Callable) -> Optional[set]:
    """
    The parameter names a builder will accept, or None if it takes **kwargs.

    Filtering the splat against this means builders don't need a `**_kw`
    absorber just to ignore flags meant for a different stage.
    """
    try:
        sig = inspect.signature(builder)
    except (TypeError, ValueError):
        return None
    names = set()
    for name, p in sig.parameters.items():
        if p.kind is inspect.Parameter.VAR_KEYWORD:
            return None
        if p.kind in (inspect.Parameter.POSITIONAL_OR_KEYWORD, inspect.Parameter.KEYWORD_ONLY):
            names.add(name)
    return names


def run(
    script: Union[str, Path],
    stages: Mapping[str, Callable[..., cq.Workplane]],
    params: Optional[Mapping[str, object]] = None,
    argv: Optional[Sequence[str]] = None,
) -> Path:
    """
    Parse arguments, build the requested stage, and export it.

    Output is named `<project>_<stage>.stl` in the project's output/ directory,
    so every part in the repo is identifiable by filename alone. When a script
    has exactly one stage the stage argument is optional.
    """
    script = Path(script).resolve()
    project = script.parent.name
    params = params or {}
    stage_names = list(stages)

    # The calling module's docstring is the script's usage text.
    caller = inspect.currentframe().f_back
    doc = caller.f_globals.get("__doc__") if caller else None

    parser = argparse.ArgumentParser(
        description=doc,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    if len(stage_names) == 1:
        parser.add_argument("stage", nargs="?", default=stage_names[0],
                            choices=stage_names, help="Build stage to export.")
    else:
        parser.add_argument("stage", choices=stage_names, help="Build stage to export.")
    parser.add_argument("-o", "--output-dir", default=str(script.parent / "output"),
                        help="Where to write the STL (default: the project's output/).")

    for key, value in params.items():
        default, help_text, kind = _spec(value)
        parser.add_argument("--" + key.replace("_", "-"), type=kind,
                            default=default, help=help_text)

    args = parser.parse_args(argv)

    overrides: Dict[str, object] = {
        key: getattr(args, key) for key in params
    }

    builder = stages[args.stage]
    accepted = _accepted_kwargs(builder)
    if accepted is not None:
        overrides = {k: v for k, v in overrides.items() if k in accepted}

    body = builder(**overrides)
    return to_stl(body, f"{project}_{args.stage}", output_dir=args.output_dir)
