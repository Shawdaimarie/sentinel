"""Preflight protection against accidental CLI source/artifact path collisions."""

from collections.abc import Mapping
from pathlib import Path


def _same_file(left: Path, right: Path) -> bool:
    if left.resolve() == right.resolve():
        return True
    try:
        return left.samefile(right)
    except FileNotFoundError:
        return False


def validate_artifact_paths(inputs: Mapping[str, Path], outputs: Mapping[str, Path]) -> None:
    """Reject input/output and output/output aliases before any artifact is written.

    Inputs may share a file (e.g. a candidate compared against itself). This is
    an accidental-overwrite guard, not protection from concurrent path replacement.
    """
    checked: dict[str, Path] = dict(inputs)
    for label, path in outputs.items():
        for other_label, other_path in checked.items():
            if _same_file(path, other_path):
                raise ValueError(f"{label} overlaps {other_label}: {path}")
        checked[label] = path
