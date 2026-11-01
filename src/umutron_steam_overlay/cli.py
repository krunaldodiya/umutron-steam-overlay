"""Command line entry point for the UmuTron Steam overlay."""

from __future__ import annotations

import os
from pathlib import Path
import shutil
import sys

from .overlay import OverlayError
from .paths import GameOverlay
from .runner import run_wrapped

USAGE = """usage:
  umutron-steam-overlay run %command%
  umutron-steam-overlay launch-option
  umutron-steam-overlay doctor
  umutron-steam-overlay inspect -- %command%

Steam launch option for a game with a UmuTron fixes folder:

  /path/to/umutron-steam-overlay run %command%
"""


def launch_option() -> str:
    executable = shutil.which("umutron-steam-overlay")
    if executable:
        return f"{executable} run %command%"
    return f"{sys.executable} -m umutron_steam_overlay run %command%"


def doctor() -> int:
    fuse = shutil.which("fuse-overlayfs")
    unmount = shutil.which("fusermount3") or shutil.which("fusermount")
    print(f"fuse-overlayfs: {fuse or 'MISSING'}")
    print(f"unmount tool:   {unmount or 'MISSING'}")
    return 0 if fuse and unmount else 1


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        print(USAGE, file=sys.stderr)
        return 2
    if args[0] in ("-h", "--help", "help"):
        print(USAGE)
        return 0
    if args[0] == "launch-option":
        print(launch_option())
        return 0
    if args[0] == "doctor":
        return doctor()
    if args[0] == "inspect":
        args.pop(0)
        if args[:1] == ["--"]:
            args.pop(0)
        try:
            return run_wrapped(args, dry_run=True, cwd=Path.cwd())
        except OverlayError as error:
            print(f"umutron-steam-overlay: {error}", file=sys.stderr)
            return 1
    if args[0] == "run":
        args.pop(0)
        if args[:1] == ["--"]:
            args.pop(0)
    # Compatibility: Steam can invoke this binary without the "run" verb.
    try:
        return run_wrapped(args, cwd=Path.cwd())
    except OverlayError as error:
        print(f"umutron-steam-overlay: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
