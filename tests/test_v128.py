import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import hyprlock, theme  # noqa: E402


class LockLayouts(unittest.TestCase):
    def test_every_layout_places_all_elements(self):
        for lay in hyprlock.LAYOUTS:
            s = hyprlock.lock_state({"layout": lay, "avatar": True})
            pos = hyprlock.place(s)
            self.assertEqual(set(pos), {"avatar", "clock", "date", "greet", "input"}, lay)
            conf = hyprlock.lock_conf(s, "/w.png")
            self.assertEqual(conf.count("halign ="), 5, lay)

    def test_bottom_left_stacks_from_the_corner(self):
        pos = hyprlock.place(hyprlock.lock_state({"layout": "bottom_left"}))
        self.assertEqual(pos["input"][2:], ("left", "bottom"))
        self.assertTrue(pos["input"][1] < pos["greet"][1] < pos["date"][1] < pos["clock"][1])
        conf = hyprlock.lock_conf(hyprlock.lock_state({"layout": "bottom_left"}))
        self.assertIn("text_align = left", conf)

    def test_split_and_presets(self):
        pos = hyprlock.place(hyprlock.lock_state({"layout": "split"}))
        self.assertEqual(pos["clock"][2:], ("left", "top"))
        self.assertEqual(pos["input"][2:], ("right", "bottom"))
        self.assertGreaterEqual(len(hyprlock.PRESETS), 20)
        self.assertGreaterEqual(len({hyprlock.preset_state(n)["layout"] for n in hyprlock.PRESETS}), 8)
        self.assertEqual(hyprlock.lock_state({"layout": "nope"})["layout"], "center")


class Accents(unittest.TestCase):
    def test_new_colours_and_readable_text(self):
        for name in ("orange", "white", "mint"):
            self.assertIn(name, theme.THEMES)
        self.assertEqual(theme.on_accent(theme.THEMES["white"]), theme.BG)
        self.assertEqual(theme.on_accent(theme.THEMES["mint"]), theme.BG)
        self.assertEqual(theme.on_accent(theme.THEMES["blue"]), "#ffffff")
        self.assertIn(f"color: {theme.BG}", theme.qss(theme.THEMES["white"]))


if __name__ == "__main__":
    unittest.main()
