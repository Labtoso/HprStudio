import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import model, packages  # noqa: E402

START = "systemctl --user start hyprpolkitagent"


class Polkit(unittest.TestCase):
    def test_written_once_lua_and_conf(self):
        s = model.hypr_state({"polkit_agent": True, "polkit_managed": True, "autostart": [START, "nm-applet"]})
        lua = model.hypr_lua(s)
        self.assertEqual(lua.count(START), 1)
        self.assertIn('hl.on("hyprland.start", function ()', lua)
        self.assertIn(f'    hl.exec_cmd("{START}")', lua)
        conf = model.hypr_conf(s)
        self.assertEqual(conf.count(f"exec-once = {START}"), 1)
        self.assertIn("exec-once = nm-applet", conf)

    def test_off_removes_entry(self):
        s = model.hypr_state({"polkit_agent": False, "polkit_managed": True, "autostart": [START]})
        self.assertNotIn("hyprpolkitagent", model.hypr_lua(s))
        self.assertNotIn("hyprpolkitagent", model.hypr_conf(s))
        # nie geschaltet: eigener Eintrag in der Autostart-Liste bleibt unangetastet
        s = model.hypr_state({"autostart": [START]})
        self.assertIn(START, model.hypr_conf(s))

    def test_detect_and_comment_foreign(self):
        with tempfile.TemporaryDirectory() as d:
            hdir = Path(d)
            main = hdir / "hyprland.lua"
            main.write_text('hl.on("hyprland.start", function()\n'
                            '  hl.exec_cmd("/usr/lib/hyprpolkitagent/hyprpolkitagent")\n'
                            '  hl.exec_cmd("waybar")\nend)\n', encoding="utf-8")
            old = model.FORMAT
            model.FORMAT = "lua"
            try:
                s = model.hypr_state(None)
                self.assertTrue(model.detect_polkit(hdir, s))
                s.update(polkit_agent=True, polkit_managed=True)
                self.assertEqual(model.manage_polkit_autostart(hdir, s, lambda *_: None), 1)
                text = main.read_text(encoding="utf-8")
                self.assertIn("-- [Hypr Studio]", text)
                self.assertIn('  hl.exec_cmd("waybar")', text)
                self.assertFalse(model.detect_polkit(hdir, model.hypr_state(None)))
            finally:
                model.FORMAT = old

    def test_conf_detect(self):
        self.assertEqual(model.foreign_polkit_lines(f"exec-once = {START}\n# exec-once = {START}\n", "conf"), [0])
        self.assertFalse(model._is_polkit_cmd("hyprpolkitagent & waybar"))

    def test_package(self):
        self.assertIn("hyprpolkitagent", packages.PACKAGES)
        self.assertEqual(packages.PACKAGES["hyprpolkitagent"][2]["pacman"], ["hyprpolkitagent"])


if __name__ == "__main__":
    unittest.main()
