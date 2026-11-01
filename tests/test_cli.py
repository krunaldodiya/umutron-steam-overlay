import unittest

from umutron_steam_overlay.cli import launch_option, main


class CliTests(unittest.TestCase):
    def test_launch_option_contains_command_placeholder(self):
        self.assertIn("%command%", launch_option())
        self.assertIn("umutron_steam_overlay", launch_option())

    def test_help(self):
        self.assertEqual(main(["help"]), 0)


if __name__ == "__main__":
    unittest.main()
