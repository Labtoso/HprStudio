import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import packages  # noqa: E402


class Packages(unittest.TestCase):
    def test_command(self):
        self.assertEqual(packages.command(["rofi", "screenshot"], "pacman"),
                         ["pacman", "-S", "--needed", "--noconfirm", "rofi", "grim", "slurp", "wl-clipboard"])
        self.assertEqual(packages.command(["rofi"], "dnf"), ["dnf", "install", "-y", "rofi-wayland"])
        self.assertEqual(packages.command(["nerdfont"], "apt"), [])

    def test_every_package_has_pacman(self):
        for k, (g, check, pkgs) in packages.PACKAGES.items():
            self.assertIn(g, packages.GROUPS)
            self.assertTrue(pkgs.get("pacman"), k)


if __name__ == "__main__":
    unittest.main()
