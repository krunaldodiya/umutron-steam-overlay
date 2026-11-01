"""Locate the UmuTron game and fixes folders from a Steam command line."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
from typing import Iterable


class OverlayPathError(ValueError):
    """A game root could not be mapped to a safe fixes folder."""


def _is_umuapps_game(path: Path) -> bool:
    return (
        path.is_absolute()
        and path.parent.name == "common"
        and path.parent.parent.name == "umuapps"
        and path.is_dir()
    )


def _candidate_from_path(value: str) -> Path | None:
    raw = Path(value)
    if not raw:
        return None
    try:
        absolute = raw if raw.is_absolute() else (Path.cwd() / raw)
    except (OSError, RuntimeError):
        return None
    parts = absolute.parts
    for index in range(len(parts) - 1, -1, -1):
        if parts[index] != "common" or index + 1 >= len(parts):
            continue
        candidate = Path(*parts[: index + 2])
        if _is_umuapps_game(candidate):
            return candidate.resolve()
    return None


def find_game_root(argv: Iterable[str], cwd: Path | None = None) -> Path | None:
    """Return ``<library>/umuapps/common/<game>`` from a Steam argv or cwd."""
    for value in argv:
        if not isinstance(value, str) or not value:
            continue
        found = _candidate_from_path(value)
        if found is not None:
            return found
    if cwd is not None:
        try:
            current = Path(cwd).resolve()
        except (OSError, RuntimeError):
            return None
        for parent in (current, *current.parents):
            if _is_umuapps_game(parent):
                return parent.resolve()
    return None


def fixes_for(common: Path) -> Path:
    return common.parent.parent / "fixes" / common.name


@dataclass(frozen=True)
class GameOverlay:
    """One installed game and its optional fixes directory."""

    common: Path
    fixes: Path

    @classmethod
    def detect(cls, argv: Iterable[str], cwd: Path | None = None) -> "GameOverlay | None":
        common = find_game_root(argv, cwd)
        if common is None:
            return None
        fixes = fixes_for(common)
        if fixes.is_symlink() or not fixes.is_dir():
            return None
        try:
            if not any(entry.is_file() or entry.is_dir() for entry in fixes.iterdir()):
                return None
        except OSError:
            return None
        return cls(common=common, fixes=fixes.resolve())

    def rewrite_arg(self, value: str, merged: Path) -> str:
        """Replace one common-folder path prefix with the merged overlay path."""
        common = str(self.common)
        merged_value = str(merged)
        if common not in value:
            return value
        return value.replace(common, merged_value)

    def rewrite_cwd(self, cwd: Path | str, merged: Path) -> Path:
        try:
            current = Path(cwd).resolve()
            relative = current.relative_to(self.common)
        except (OSError, RuntimeError, ValueError):
            return Path(cwd)
        return merged / relative
