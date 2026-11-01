"""Read-only fuse-overlayfs sessions for Steam-launched games."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import uuid

from .paths import GameOverlay


class OverlayError(RuntimeError):
    """The fixes overlay could not be mounted safely."""


def _require_tool(name: str) -> str:
    found = shutil.which(name)
    if not found:
        raise OverlayError(f"{name} is not installed.")
    return found


class OverlaySession:
    """One transient read-only view of ``fixes`` over ``common``."""

    def __init__(self, game: GameOverlay) -> None:
        self.game = game
        self.base = Path(tempfile.gettempdir()) / f"umutron-steam-overlay-{os.getuid()}"
        self.directory = self.base / (
            hashlib.sha256(str(game.common).encode("utf-8")).hexdigest()[:10]
            + "-"
            + uuid.uuid4().hex[:12]
        )
        self.upper = self.directory / "upper"
        self.work = self.directory / "work"
        self.merged = self.directory / "merged"
        self._mounted = False

    def mount(self) -> Path:
        if self._mounted:
            return self.merged
        fuse = _require_tool("fuse-overlayfs")
        unmount = shutil.which("fusermount3") or shutil.which("fusermount")
        if not unmount:
            raise OverlayError("fusermount3/fusermount is not installed.")
        try:
            self.base.mkdir(parents=True, exist_ok=True, mode=0o700)
            if self.base.is_symlink():
                raise OverlayError("The overlay runtime directory is a symbolic link.")
            os.chmod(self.base, 0o700)
            self.directory.mkdir(mode=0o700)
            self.upper.mkdir(mode=0o700)
            self.work.mkdir(mode=0o700)
            self.merged.mkdir(mode=0o700)
        except OSError as error:
            self.cleanup()
            raise OverlayError("Could not create the overlay runtime directory.") from error
        command = [
            fuse,
            "-o",
            f"lowerdir={self.game.fixes}:{self.game.common},upperdir={self.upper},workdir={self.work}",
            "-o",
            "ro,nosuid,nodev",
            str(self.merged),
        ]
        try:
            result = subprocess.run(
                command,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=20,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            self.cleanup()
            raise OverlayError("The fixes overlay could not be mounted.") from error
        if result.returncode != 0:
            detail = result.stderr.decode("utf-8", errors="replace").strip()
            self.cleanup()
            raise OverlayError(
                "The fixes overlay could not be mounted."
                + (": " + detail if detail else "")
            )
        if not os.path.ismount(self.merged):
            self.cleanup()
            raise OverlayError("The fixes overlay did not become a mountpoint.")
        self._mounted = True
        return self.merged

    def cleanup(self) -> None:
        if self._mounted:
            for name, arguments in (
                ("fusermount3", ["-u", str(self.merged)]),
                ("fusermount", ["-u", str(self.merged)]),
                ("fusermount3", ["-uz", str(self.merged)]),
                ("fusermount", ["-uz", str(self.merged)]),
            ):
                tool = shutil.which(name)
                if not tool:
                    continue
                if not os.path.ismount(self.merged):
                    break
                try:
                    subprocess.run(
                        [tool, *arguments],
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=10,
                        check=False,
                    )
                except (OSError, subprocess.TimeoutExpired):
                    pass
            self._mounted = False
        if os.path.ismount(self.merged):
            raise OverlayError(f"Could not unmount {self.merged}.")
        shutil.rmtree(self.directory, ignore_errors=True)

    def __enter__(self) -> "OverlaySession":
        self.mount()
        return self

    def __exit__(self, *_exc) -> None:
        self.cleanup()
