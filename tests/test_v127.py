import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import hardware, laptopkeys, model  # noqa: E402


class AutoLaptop(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.home = Path(self.tmp.name)
        self.hdir = self.home / "hypr"
        self.hdir.mkdir()
        (self.hdir / "hyprland.lua").write_text('hl.bind("XF86AudioMute", hl.dsp.exec_cmd("x"))\n', encoding="utf-8")
        self.saved = (model.FORMAT, model.config_home, hardware.detect, model.run)
        model.FORMAT = "lua"
        model.config_home = lambda: self.home
        hardware.detect = lambda: {"vendor": "Lenovo", "model": "IdeaPad", "laptop": True, "backlight": [], "battery": True}
        self.cmds = []
        model.run = lambda cmd, log, quiet=False: self.cmds.append(cmd) or True

    def tearDown(self):
        model.FORMAT, model.config_home, hardware.detect, model.run = self.saved
        self.tmp.cleanup()

    def test_works_without_any_setting(self):
        s = model.hypr_state(None)
        self.assertTrue(laptopkeys.auto(s, lambda *_: None))
        self.assertTrue(s["laptop_keys"] and s["laptop_managed"])
        main = (self.hdir / "hyprland.lua").read_text(encoding="utf-8")
        self.assertEqual(main.count('require("hyprstudio_laptop")'), 1)
        self.assertIn('-- [Hypr Studio] hl.bind("XF86AudioMute"', main)  # nichts doppelt
        self.assertIn("XF86MonBrightnessDown", (self.hdir / "hyprstudio_laptop.lua").read_text(encoding="utf-8"))
        self.assertIn(["hyprctl", "reload"], self.cmds)
        self.assertFalse(model._has_include(main, "lua"))  # Hauptdesign von Hypr Studio bleibt aus
        # zweiter Start: nichts doppelt, kein Neuladen nötig
        self.cmds.clear()
        self.assertFalse(laptopkeys.auto(s, lambda *_: None))
        self.assertEqual((self.hdir / "hyprland.lua").read_text(encoding="utf-8").count('require("hyprstudio_laptop")'), 1)
        self.assertEqual(self.cmds, [])

    def test_user_choice_off_is_kept(self):
        s = model.hypr_state({"laptop_keys": False, "laptop_managed": True})
        laptopkeys.auto(s, lambda *_: None)
        self.assertFalse(s["laptop_keys"])
        self.assertNotIn("XF86", (self.hdir / "hyprstudio_laptop.lua").read_text(encoding="utf-8").split("\n", 1)[1])

    def test_desktop_untouched(self):
        hardware.detect = lambda: {"vendor": "", "model": "", "laptop": False, "backlight": [], "battery": False}
        s = model.hypr_state(None)
        self.assertFalse(laptopkeys.auto(s, lambda *_: None) and s["laptop_keys"])
        self.assertFalse((self.hdir / "hyprstudio_laptop.lua").exists())

    def test_moves_old_binds_out_of_hyprstudio_lua(self):
        (self.hdir / "hyprstudio.lua").write_text('-- x\nhl.bind("XF86AudioMute", hl.dsp.exec_cmd("y"))\n', encoding="utf-8")
        laptopkeys.auto(model.hypr_state(None), lambda *_: None)
        self.assertNotIn("XF86", (self.hdir / "hyprstudio.lua").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
