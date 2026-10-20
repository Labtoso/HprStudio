import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import applauncher as al, launcher, model  # noqa: E402

DESK = {
    "hyprstudio.desktop": "[Desktop Entry]\nType=Application\nName=Hypr Studio\nExec=hypr-studio %U\nIcon=hs\n",
    "why.desktop": "[Desktop Entry]\nType=Application\nName=Why Hyper\nExec=why\n",
    "htop.desktop": "[Desktop Entry]\nType=Application\nName=Htop\nName[de]=Htop DE\nExec=htop\nTerminal=true\n",
    "hidden.desktop": "[Desktop Entry]\nType=Application\nName=Hyper Hidden\nExec=x\nNoDisplay=true\n",
    "link.desktop": "[Desktop Entry]\nType=Link\nName=Hylink\nURL=x\n",
    "zen.desktop": "[Desktop Entry]\nType=Application\nName=Zen Browser\nExec=zen-browser %u\n"
                   "[Desktop Action new]\nName=Hy action\nExec=zen --new\n",
}


class LLauncher(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name) / "applications"
        d.mkdir()
        for n, txt in DESK.items():
            (d / n).write_text(txt, encoding="utf-8")
        self.apps = al.load_apps([d])

    def tearDown(self):
        self.tmp.cleanup()

    def names(self, q, hist=None):
        return [a["name"] for a in al.filter_apps(self.apps, q, hist or {})]

    def test_strict_prefix_every_letter(self):
        self.assertEqual(self.names("h"), ["Htop", "Hypr Studio"])
        self.assertEqual(self.names("hy"), ["Hypr Studio"])
        self.assertEqual(self.names("HYPR S"), ["Hypr Studio"])
        self.assertEqual(self.names("z"), ["Zen Browser"])
        self.assertEqual(self.names("x"), [])
        self.assertEqual(len(self.names("")), 4)

    def test_history_first(self):
        self.assertEqual(self.names("h", {"hyprstudio.desktop": 3}), ["Hypr Studio", "Htop"])

    def test_command(self):
        hs = next(a for a in self.apps if a["name"] == "Hypr Studio")
        self.assertEqual(al.command(hs), "hypr-studio")
        top = next(a for a in self.apps if a["id"] == "htop.desktop")
        self.assertEqual(al.command(top, "kitty"), "kitty -e htop")

    def test_localized_name(self):
        txt = DESK["htop.desktop"]
        self.assertEqual(al.parse_desktop(txt, ["Name[de]", "Name"])["name"], "Htop DE")

    def test_tab_integration(self):
        self.assertIn("llauncher", launcher.APPS)
        self.assertTrue(model.is_launcher_cmd("l-launcher"))
        with tempfile.TemporaryDirectory() as d:
            files = launcher.files(launcher.state({"app": "llauncher"}), Path(d))
            self.assertEqual(files[0][0].name, "l-launcher.json")
        self.assertIn('class = "l-launcher"', model.hypr_lua(model.hypr_state(None)))


class LauncherAction(unittest.TestCase):
    def test_output_and_import(self):
        b = {"mods": ["SUPER"], "key": "R", "action": "launcher", "arg": "llauncher", "flags": []}
        self.assertTrue(model.bind_ok(b))
        self.assertIn('hl.dsp.exec_cmd("l-launcher")', model.bind_lua(b))
        self.assertIn("bind = SUPER, R, exec, pkill -x wofi || wofi --show drun", model.bind_conf(dict(b, arg="wofi")))
        model.LAUNCHER_TOGGLE = False
        try:
            self.assertIn("bind = SUPER, R, exec, wofi --show drun", model.bind_conf(dict(b, arg="wofi")))
        finally:
            model.LAUNCHER_TOGGLE = True
        binds, _ = model.import_conf("bind = SUPER, D, exec, pkill -x rofi || rofi -show drun")
        self.assertEqual((binds[0]["action"], binds[0]["arg"]), ("launcher", "rofi"))
        self.assertTrue(model.is_launcher_cmd("pkill -x fuzzel || fuzzel"))
        self.assertFalse(model.bind_ok(dict(b, arg="xyz")))
        binds, _ = model.import_lua('hl.bind("SUPER + R", hl.dsp.exec_cmd("rofi -show drun"))\n')
        self.assertEqual((binds[0]["action"], binds[0]["arg"]), ("launcher", "rofi"))
        binds, _ = model.import_conf("bind = SUPER, D, exec, fuzzel\n")
        self.assertEqual((binds[0]["action"], binds[0]["arg"]), ("launcher", "fuzzel"))
        self.assertEqual(model.bind_cmd(b), "l-launcher")


class AllLaunchers(unittest.TestCase):
    def test_all_configs_written(self):
        with tempfile.TemporaryDirectory() as d:
            names = [p.name for p, _ in launcher.files(launcher.state({"app": "rofi", "position": "center"}), Path(d))]
            self.assertEqual(names[0], "config.rasi")
            for n in ("config", "style.css", "fuzzel.ini", "l-launcher.json"):
                self.assertIn(n, names)
            wofi = dict(launcher.files(launcher.state({"app": "rofi"}), Path(d)))[Path(d) / "wofi" / "config"]
            self.assertIn("location=center", wofi)


class InstallErrors(unittest.TestCase):
    def test_reasons(self):
        from hyprstudio import packages
        self.assertEqual(packages.fail_reason("error: failed retrieving file 'fuzzel-1.zst' from x : 404"), "pkg.err_sync")
        self.assertEqual(packages.fail_reason("error: target not found: fuzel"), "pkg.err_notfound")
        self.assertEqual(packages.fail_reason("error: unable to lock database"), "pkg.err_lock")
        self.assertIsNone(packages.fail_reason("all fine"))
