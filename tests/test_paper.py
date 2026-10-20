import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import paper  # noqa: E402


class Paper(unittest.TestCase):
    def test_conf(self):
        s = paper.paper_state({"path": "~/Bilder/wald.jpg", "fit": "contain",
                               "monitors": {"DP-1": {"path": "~/Bilder/Wallpaper", "fit": "fill"}, "x": "kaputt"},
                               "random": True})
        c = paper.paper_conf(s)
        self.assertIn("wallpaper {\n    monitor = DP-1\n    path = ~/Bilder/Wallpaper\n    fit_mode = fill\n"
                      "    timeout = 30\n    order = random\n}", c)
        self.assertIn("wallpaper {\n    monitor = \n    path = ~/Bilder/wald.jpg\n    fit_mode = contain\n}", c)
        self.assertIn("splash = false", c)
        self.assertNotIn("monitor = x", c)
        self.assertEqual(c.count("{"), c.count("}"))

    def test_apply(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprpaper.conf").write_text("preload = alt\n", encoding="utf-8")
            ok, _ = paper.apply_paper(paper.paper_state({"path": "/b.png"}), h, lambda *_: None)
            self.assertTrue(ok)
            self.assertTrue((h / "hyprpaper.conf.hyprstudio-original").is_file())
            self.assertFalse(paper.apply_paper(paper.paper_state(None), h, lambda *_: None)[0])

    def test_cursor_scan(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            (root / "Bibata" / "cursors").mkdir(parents=True)
            (root / "Hypr-Bibata").mkdir()
            (root / "Hypr-Bibata" / "manifest.hl").write_text("", encoding="utf-8")
            (root / "Papirus").mkdir()
            old = paper.icon_dirs
            paper.icon_dirs = lambda: [root]
            try:
                self.assertEqual(paper.cursor_themes(), [("Bibata", "xcursor"), ("Hypr-Bibata", "hyprcursor")])
            finally:
                paper.icon_dirs = old


if __name__ == "__main__":
    unittest.main()
