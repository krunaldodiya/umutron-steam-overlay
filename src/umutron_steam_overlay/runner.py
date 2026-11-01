"""Run a Steam %command% through the fixes overlay."""

from __future__ import annotations

import json
import os
from pathlib import Path
import signal
import subprocess
import sys

from .overlay import OverlaySession
from .paths import GameOverlay


def _print_error(message: str) -> None:
    print(f"umutron-steam-overlay: {message}", file=sys.stderr)


def run_wrapped(argv: list[str], *, dry_run: bool = False, cwd: Path | None = None) -> int:
    """Launch ``argv`` with fixes overlaid, or execute it unchanged.

    The wrapper deliberately stays as the Steam-visible parent process so the
    read-only FUSE mount can be unmounted after the game exits.
    """
    if not argv:
        _print_error("no command was supplied")
        return 2
    current = Path(cwd or os.getcwd())
    overlay = GameOverlay.detect(argv, current)
    if overlay is None:
        # No fixes for this game: Steam's original command must be untouched.
        if dry_run:
            print(json.dumps({"overlay": False, "argv": argv}, indent=2))
            return 0
        try:
            os.chdir(current)
            os.execvpe(argv[0], argv, os.environ)
        except OSError as error:
            _print_error(f"could not run {argv[0]}: {error}")
            return 127

    session = OverlaySession(overlay)
    try:
        merged = session.mount()
        mapped = [overlay.rewrite_arg(arg, merged) for arg in argv]
        mapped_cwd = overlay.rewrite_cwd(current, merged)
        environment = dict(os.environ)
        environment["PWD"] = str(mapped_cwd)
        environment["OLDPWD"] = str(current)
        if dry_run:
            print(
                json.dumps(
                    {
                        "overlay": True,
                        "common": str(overlay.common),
                        "fixes": str(overlay.fixes),
                        "merged": str(merged),
                        "cwd": str(mapped_cwd),
                        "argv": mapped,
                    },
                    indent=2,
                )
            )
            return 0
        try:
            child = subprocess.Popen(mapped, cwd=mapped_cwd, env=environment)
        except OSError as error:
            _print_error(f"could not run {mapped[0]}: {error}")
            return 127

        def forward(signum, _frame):
            try:
                child.send_signal(signum)
            except OSError:
                pass

        previous = {}
        for signum in (signal.SIGINT, signal.SIGTERM, signal.SIGHUP):
            previous[signum] = signal.signal(signum, forward)
        try:
            code = child.wait()
        finally:
            for signum, handler in previous.items():
                signal.signal(signum, handler)
        return 128 + (-code) if code < 0 else code
    except Exception as error:
        _print_error(str(error))
        return 1
    finally:
        try:
            session.cleanup()
        except Exception as error:
            _print_error(f"cleanup failed: {error}")
