import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import launcher, model, reset  # noqa: E402

LOG = (lambda *_: None)


class Reset(unittest.TestCase):
    def test_default_lua_is_importable(self):
        binds, _ = model.import_lua(reset.DEFAULT_LUA)
        self.assertGreater(len(binds), 30)
        self.assertEqual(reset.DEFAULT_LUA.count("{"), reset.DEFAULT_LUA.count("}"))
        self.assertEqual(reset.DEFAULT_LUA.count("("), reset.DEFAULT_LUA.count(")"))

    def test_reset_all(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d)
            h = c / "hypr"
            h.mkdir()
            (h / "hyprland.lua").write_text('local mainMod = "SUPER"\nhl.bind(mainMod .. " + Q", hl.dsp.exec_cmd("kitty"))\n',
                                            encoding="utf-8")
            model.apply_hypr(model.hypr_state(None), h, LOG)
            model.import_binds(h, LOG)  # kommentiert SUPER+Q aus
            w = c / "waybar"
            w.mkdir()
            (w / "config").write_text("{}", encoding="utf-8")
            model.apply_waybar(model.waybar_state(None), w, LOG)
            launcher.apply(launcher.state({"app": "fuzzel"}), c, LOG)

            reset.reset_all(c, False, LOG)
            text = (h / "hyprland.lua").read_text(encoding="utf-8")
            self.assertNotIn("hyprstudio", text)
            self.assertIn('hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd("kitty"))', text)
            self.assertNotIn("[Hypr Studio", text)
            self.assertEqual((w / "config").read_text(encoding="utf-8"), "{}")
            self.assertFalse((c / "fuzzel" / "fuzzel.ini").exists())
            self.assertEqual(len(list((c / "fuzzel").glob("fuzzel.ini.hyprstudio-*"))), 1)
            self.assertTrue((h / "hyprstudio.lua").is_file())  # nichts gelöscht

            reset.reset_all(c, True, LOG)
            self.assertEqual((h / "hyprland.lua").read_text(encoding="utf-8"), reset.DEFAULT_LUA)
            self.assertGreaterEqual(len(list(h.glob("hyprland.lua.hyprstudio-*"))), 1)


if __name__ == "__main__":
    unittest.main()
