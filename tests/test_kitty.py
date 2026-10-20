import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import kitty, reset  # noqa: E402

LOG = (lambda *_: None)


class Kitty(unittest.TestCase):
    def test_mine_matches_vault_config(self):
        c = kitty.conf(kitty.preset("mine"))
        for line in ("font_family        JetBrainsMono Nerd Font", "font_size          11.5",
                     "background_opacity          0.7", "background_blur             0",
                     "linux_display_server        x11", "hide_window_decorations  no", "window_padding_width     14",
                     "cursor_shape             beam", "cursor_blink_interval    0", "cursor_trail             3",
                     "tab_bar_style         powerline", "tab_powerline_style   slanted",
                     'tab_title_template    "{index}: {title}"', "background            #1a1b26",
                     "color0  #15161e", "color15 #c0caf5"):
            self.assertIn(line, c)

    def test_presets(self):
        for name in kitty.PRESETS:
            c = kitty.conf(kitty.preset(name))
            self.assertEqual(sum(ln.startswith("color") for ln in c.splitlines()), 16, name)
        self.assertNotIn("linux_display_server", kitty.conf(kitty.preset("tokyo")))

    def test_blink_curve(self):
        s = kitty.state({"blink": 0.5, "blink_curve": "linear"})
        self.assertIn("cursor_blink_interval    0.5 linear", kitty.conf(s))

    def test_apply_include_undo_reset(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d)
            (c / "kitty").mkdir()
            (c / "kitty" / "kitty.conf").write_text("font_size 10\n", encoding="utf-8")
            s = kitty.state(None)
            kitty.apply(s, c, LOG)
            kitty.apply(s, c, LOG)
            main = (c / "kitty" / "kitty.conf").read_text(encoding="utf-8")
            self.assertEqual(main.count(kitty.INCLUDE), 1)
            self.assertTrue(main.startswith("font_size 10"))
            s["opacity"] = 0.5
            kitty.apply(s, c, LOG)
            self.assertTrue(kitty.undo(c, LOG))
            self.assertIn("background_opacity          0.85", (c / "kitty" / "hyprstudio.conf").read_text(encoding="utf-8"))
            reset.reset_all(c, False, LOG)
            self.assertNotIn(kitty.INCLUDE, (c / "kitty" / "kitty.conf").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
