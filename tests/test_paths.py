from pathlib import Path
import unittest

from umutron_steam_overlay.paths import GameOverlay, find_game_root


class PathTests(unittest.TestCase):
    def setUp(self):
        import tempfile

        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.common = self.root / "umuapps" / "common" / "Test Game"
        self.fixes = self.root / "umuapps" / "fixes" / "Test Game"
        self.common.mkdir(parents=True)
        self.fixes.mkdir(parents=True)
        (self.fixes / "patch.dll").write_bytes(b"fix")

    def tearDown(self):
        self.temp.cleanup()

    def test_finds_game_from_command_argument(self):
        exe = self.common / "Game.exe"
        exe.write_bytes(b"exe")
        self.assertEqual(find_game_root(["/usr/bin/proton", str(exe)]), self.common.resolve())

    def test_finds_game_from_working_directory(self):
        self.assertEqual(find_game_root([], self.common / "subdir"), self.common.resolve())

    def test_requires_a_fixes_directory(self):
        (self.fixes / "patch.dll").unlink()
        (self.fixes / "patch.dll").parent.rmdir()
        self.assertIsNone(GameOverlay.detect([str(self.common / "Game.exe")]))

    def test_rewrites_only_common_prefix(self):
        overlay = GameOverlay.detect([str(self.common / "Game.exe")])
        self.assertIsNotNone(overlay)
        merged = Path("/tmp/merged")
        self.assertEqual(
            overlay.rewrite_arg(str(self.common / "Game.exe"), merged),
            str(merged / "Game.exe"),
        )
        self.assertEqual(
            overlay.rewrite_arg(f"--path={self.common / 'data.txt'}", merged),
            f"--path={merged / 'data.txt'}",
        )
        self.assertEqual(overlay.rewrite_arg("/unrelated/path", merged), "/unrelated/path")

    def test_rewrites_cwd_inside_game(self):
        overlay = GameOverlay.detect([str(self.common / "Game.exe")])
        self.assertIsNotNone(overlay)
        merged = Path("/tmp/merged")
        self.assertEqual(
            overlay.rewrite_cwd(self.common / "bin", merged),
            merged / "bin",
        )
        self.assertEqual(overlay.rewrite_cwd(Path("/unrelated"), merged), Path("/unrelated"))


if __name__ == "__main__":
    unittest.main()
