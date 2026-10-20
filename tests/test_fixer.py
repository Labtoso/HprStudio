import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import fixer, model  # noqa: E402


class Fixer(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.h = Path(self.tmp.name)
        self.s = model.hypr_state({"gesture": 3, "smart_gaps": True, "binds": model.TEMPLATES["basics"]})
        self.lua = self.h / "hyprstudio.lua"
        self.lua.write_text(model.hypr_lua(self.s), encoding="utf-8")
        self.lines = self.lua.read_text(encoding="utf-8").splitlines()

    def tearDown(self):
        self.tmp.cleanup()

    def n(self, start):
        return next(i + 1 for i, ln in enumerate(self.lines) if ln.strip().startswith(start))

    def err(self, line, msg="unknown option"):
        return f'require("hyprstudio"): {self.lua.as_posix()}:{line}: {msg}'

    def test_parse_both_formats(self):
        a, b = fixer.parse([self.err(5, "boom"),
                            "Config error in file /home/u/.config/hypr/hyprland.conf at line 42: config option <x> does not exist."])
        self.assertEqual((a["line"], a["msg"]), (5, "boom"))
        self.assertTrue(a["file"].endswith("hyprstudio.lua"))
        self.assertEqual((b["file"], b["line"]), ("/home/u/.config/hypr/hyprland.conf", 42))
        self.assertEqual(fixer.parse(["irgendwas"])[0]["line"], 0)

    def test_option_skip(self):
        e = fixer.parse([self.err(self.n("xray"))])[0]
        self.assertEqual(fixer.plan(e), {"kind": "skip", "option": "decoration.blur.xray"})
        self.assertTrue(fixer.apply_fix(e, self.s, lambda *_: None))
        self.assertNotIn("xray", model.hypr_lua(self.s))
        self.assertNotIn("xray", model.hypr_conf(self.s))
        self.assertIn("vibrancy", model.hypr_lua(self.s))

    def test_nested_col(self):
        e = fixer.parse([self.err(self.n("active_border"))])[0]
        self.assertEqual(fixer.plan(e)["option"], "general.col.active_border")
        fixer.apply_fix(e, self.s, lambda *_: None)
        self.assertNotIn("col.active_border", model.hypr_conf(self.s))
        self.assertIn("col.inactive_border", model.hypr_conf(self.s))

    def test_features(self):
        for start, key, val in (("hl.gesture", "gesture", 0), ("hl.workspace_rule", "smart_gaps", False)):
            e = fixer.parse([self.err(self.n(start))])[0]
            fixer.apply_fix(e, self.s, lambda *_: None)
            self.assertEqual(self.s[key], val)

    def test_bind(self):
        e = fixer.parse([self.err(self.n('hl.bind("SUPER + M"'))])[0]
        self.assertEqual(fixer.plan(e)["kind"], "bind")
        self.assertTrue(fixer.apply_fix(e, self.s, lambda *_: None))
        self.assertNotIn("hl.dsp.exit()", model.hypr_lua(self.s))

    def test_foreign_comment(self):
        f = self.h / "hyprland.lua"
        f.write_text("a = 1\nkaputt(\nb = 2\n", encoding="utf-8")
        e = fixer.parse([f"{f.as_posix()}:2: syntax"])[0]
        self.assertEqual(fixer.plan(e)["kind"], "comment")
        self.assertTrue(fixer.apply_fix(e, self.s, lambda *_: None))
        self.assertEqual(f.read_text(encoding="utf-8").splitlines()[1], "-- [Hypr Studio Fix] kaputt(")
        self.assertFalse(fixer.apply_fix(e, self.s, lambda *_: None))  # nicht doppelt
        self.assertEqual(len(list(self.h.glob("hyprland.lua.hyprstudio-*"))), 1)

    def test_backups_restore(self):
        f = self.h / "hypr"
        f.mkdir()
        (f / "hyprland.lua").write_text("neu", encoding="utf-8")
        (f / "hyprland.lua.hyprstudio-original").write_text("alt", encoding="utf-8")
        found = fixer.backups(self.h)
        self.assertEqual(found[0][1], f / "hyprland.lua")
        fixer.restore(*found[0], lambda *_: None)
        self.assertEqual((f / "hyprland.lua").read_text(encoding="utf-8"), "alt")
        self.assertEqual(len(list(f.glob("hyprland.lua.hyprstudio-2*"))), 1)


if __name__ == "__main__":
    unittest.main()
