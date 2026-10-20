import io
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import appearance, fonts, hyprlock, model  # noqa: E402


class Fonts(unittest.TestCase):
    def test_extract_only_fonts_flat(self):
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:xz") as tar:
            for name, data in (("a/Hack-Regular.ttf", b"ttf"), ("../evil.ttf", b"x"), ("README.md", b"r"),
                               ("b/HackMono.otf", b"otf")):
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                tar.addfile(ti, io.BytesIO(data))
        with tempfile.TemporaryDirectory() as d:
            files = fonts.extract(buf.getvalue(), Path(d) / "Hack")
            self.assertEqual(sorted(f.name for f in files), ["Hack-Regular.ttf", "HackMono.otf", "evil.ttf"])
            self.assertTrue(all(f.parent == Path(d) / "Hack" for f in files))  # nichts außerhalb
            self.assertFalse((Path(d) / "evil.ttf").exists())

    def test_catalog(self):
        self.assertEqual(fonts.family_of("CascadiaCode"), "CaskaydiaCove Nerd Font")
        self.assertEqual(len({a for a, _ in fonts.CATALOG}), len(fonts.CATALOG))


class Dark(unittest.TestCase):
    def test_merge_keeps_rest(self):
        txt = "[General]\nfoo=1\n\n[KDE]\nSingleClick=false\n"
        out = appearance.merge_ini(txt, {"General": {"ColorScheme": "BreezeDark"}, "Colors:View": {"A": "1"}})
        self.assertIn("foo=1", out)
        self.assertIn("SingleClick=false", out)
        self.assertIn("ColorScheme=BreezeDark", out)
        self.assertIn("[Colors:View]\nA=1", out)

    def test_apply_writes_kate_and_kdeglobals(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            appearance.apply("dark", home, lambda *_: None)
            self.assertIn("ColorScheme=Breeze Dark", (home / "katerc").read_text())
            self.assertIn("ColorScheme=Breeze Dark", (home / "kwriterc").read_text())
            kg = (home / "kdeglobals").read_text()
            self.assertIn("ColorScheme=BreezeDark", kg)
            self.assertIn("[Colors:Window]", kg)
            appearance.apply("light", home, lambda *_: None)
            self.assertIn("ColorScheme=Breeze Light", (home / "katerc").read_text())
            self.assertIn("gtk-application-prefer-dark-theme=0", (home / "gtk-3.0/settings.ini").read_text())

    def test_qt_env(self):
        s = model.hypr_state({"qt_theme": "kde"})
        self.assertIn('hl.env("QT_QPA_PLATFORMTHEME", "kde")', model.hypr_lua(s))
        self.assertIn("env = QT_QPA_PLATFORMTHEME,kde", model.hypr_conf(s))
        self.assertNotIn("QT_QPA_PLATFORMTHEME", model.hypr_lua(model.hypr_state(None)))


class Lock(unittest.TestCase):
    def test_conf(self):
        s = hyprlock.lock_state({"avatar": True, "clock_fmt": "sec"})
        c = hyprlock.lock_conf(s)
        for part in ("general {", "path = screenshot", "input-field {", "image {", 'date +"%H:%M:%S"',
                     "outer_color = rgba(89b4faff)", "rounding = -1", "font_family = JetBrainsMono Nerd Font"):
            self.assertIn(part, c)
        y = hyprlock.layout(s)
        self.assertTrue(y["clock"] > y["date"] > y["avatar"] > y["greet"] > y["input"])

    def test_bg_and_presets(self):
        s = hyprlock.preset_state("nord")
        self.assertNotIn("path =", hyprlock.lock_conf(s))
        s = hyprlock.preset_state("glass")
        self.assertIn("path = /x.png", hyprlock.lock_conf(s, "/x.png"))
        self.assertEqual(hyprlock.lock_state({"bg": "bogus"})["bg"], "screenshot")
        ok, why = hyprlock.apply_lock(hyprlock.lock_state({"bg": "image"}), Path(tempfile.gettempdir()), print)
        self.assertEqual((ok, why), (False, "lock.nopath"))

    def test_bind(self):
        b = hyprlock.set_lock_bind([], True)
        self.assertTrue(hyprlock.has_lock_bind(b))
        self.assertEqual(model.bind_lua(b[0]).count("hyprlock"), 1)
        self.assertFalse(hyprlock.has_lock_bind(hyprlock.set_lock_bind(b, False)))


if __name__ == "__main__":
    unittest.main()
