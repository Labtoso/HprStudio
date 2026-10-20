import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import packages  # noqa: E402


class Updates(unittest.TestCase):
    def test_commands(self):
        self.assertEqual(packages.update_command(["hyprland"], "pacman"),
                         ["pacman", "-Syu", "--noconfirm", "--needed", "hyprland"])
        self.assertEqual(packages.update_command([], "pacman", everything=True), ["pacman", "-Syu", "--noconfirm"])
        self.assertEqual(packages.update_command(["waybar"], "dnf"), ["dnf", "upgrade", "-y", "waybar"])
        self.assertIn("--only-upgrade waybar", packages.update_command(["waybar"], "apt")[2])
        self.assertEqual(packages.update_command([], "pacman"), [])
        self.assertEqual(packages.update_command(["x"], None), [])

    def test_groups(self):
        self.assertEqual(set(packages.UPDATE_GROUPS), {"hyprland", "waybar", "launcher"})
        self.assertIn("hyprlock", packages.UPDATE_GROUPS["hyprland"])

    def test_font_cache(self):
        packages._FONTS.update(t=10 ** 12, out="jetbrainsmono nerd font")
        try:
            self.assertIn("jetbrainsmono", packages.font_list())
            packages.forget()
            self.assertEqual(packages._FONTS["t"], 0.0)
        finally:
            packages.forget()


if __name__ == "__main__":
    unittest.main()
