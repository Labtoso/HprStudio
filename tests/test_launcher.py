import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import launcher, model  # noqa: E402


class Launcher(unittest.TestCase):
    def test_presets_all_apps(self):
        for name in launcher.PRESETS:
            for app in launcher.APPS:
                s = launcher.preset(name, {"app": app})
                for path, data in launcher.files(s, Path("/x")):
                    if path.suffix in (".rasi", ".css"):
                        self.assertEqual(data.count("{"), data.count("}"), (name, app, path.name))

    def test_rofi(self):
        s = launcher.state({"position": "top", "offset": 40, "grid": True, "columns": 4, "icon_theme": "Papirus"})
        theme = launcher.rofi_theme(s)
        self.assertIn("location: north;", theme)
        self.assertIn("y-offset: 40px;", theme)
        self.assertIn("orientation: vertical;", theme)
        self.assertIn("columns: 4;", theme)
        cfg = launcher.rofi_config(s, "/home/u/.config/rofi/hyprstudio.rasi")
        self.assertIn('@theme "/home/u/.config/rofi/hyprstudio.rasi"', cfg)
        self.assertIn('icon-theme: "Papirus";', cfg)
        self.assertIn('font: "JetBrainsMono Nerd Font 12";', cfg)

    def test_wofi(self):
        s = launcher.state({"app": "wofi", "position": "bottom", "offset": 20})
        cfg = launcher.wofi_config(s)
        self.assertIn("location=bottom", cfg)
        self.assertIn("yoffset=-20", cfg)
        self.assertIn("allow_images=true", cfg)
        self.assertIn("#entry:selected", launcher.wofi_css(s))

    def test_fuzzel(self):
        s = launcher.state({"app": "fuzzel", "bg": "#112233cc"})
        ini = launcher.fuzzel_ini(s)
        self.assertIn("background=112233cc", ini)
        self.assertIn("[border]\nwidth=2\nradius=14", ini)
        self.assertIn("font=JetBrainsMono Nerd Font:size=12", ini)

    def test_preset_keeps_app(self):
        s = launcher.preset("grid", launcher.state({"app": "wofi", "font": "Inter"}))
        self.assertEqual((s["app"], s["font"], s["grid"]), ("wofi", "Inter", True))

    def test_apply_backup_undo(self):
        with tempfile.TemporaryDirectory() as d:
            c = Path(d)
            (c / "rofi").mkdir()
            (c / "rofi" / "config.rasi").write_text("configuration { }", encoding="utf-8")
            s = launcher.state(None)
            launcher.apply(s, c, lambda *_: None)
            self.assertTrue((c / "rofi" / "config.rasi.hyprstudio-original").is_file())
            self.assertIn(model.MARK, (c / "rofi" / "hyprstudio.rasi").read_text(encoding="utf-8"))
            s["width"] = 900
            launcher.apply(s, c, lambda *_: None)
            self.assertTrue(launcher.undo(s, c))
            self.assertIn("width: 620px;", (c / "rofi" / "hyprstudio.rasi").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
