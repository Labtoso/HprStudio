import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import appearance, kitty, launcher, model  # noqa: E402

LOG = (lambda *_: None)


class KittyStart(unittest.TestCase):
    def test_no_start_by_default(self):
        self.assertNotIn("shell ", kitty.conf(kitty.state(None)))

    def test_start_script(self):
        with tempfile.TemporaryDirectory() as d:
            s = kitty.state({"fastfetch": True, "start_cmds": ["echo hi", "  ", 3]})
            self.assertEqual(s["start_cmds"], ["echo hi"])
            kitty.apply(s, Path(d), LOG)
            sh = (Path(d) / "kitty" / kitty.START).read_text(encoding="utf-8")
            self.assertIn("fastfetch", sh)
            self.assertIn("echo hi", sh)
            self.assertTrue(sh.splitlines()[-1].startswith("exec "))
            self.assertIn(f"shell {Path(d) / 'kitty' / kitty.START}",
                          (Path(d) / "kitty" / "hyprstudio.conf").read_text(encoding="utf-8"))


class NameSearch(unittest.TestCase):
    def test_default_on(self):
        s = launcher.state(None)
        self.assertTrue(s["name_search"])
        r = launcher.rofi_config(s, "x.rasi")
        self.assertIn('matching: "prefix";', r)
        self.assertIn('drun-match-fields: "name";', r)
        self.assertIn("tokenize: false;", r)
        self.assertIn("fields=name", launcher.fuzzel_ini(s).splitlines())
        self.assertIn("match-mode=exact", launcher.fuzzel_ini(s))
        self.assertIn("matching=contains", launcher.wofi_config(s))

    def test_off(self):
        s = launcher.state({"name_search": False})
        self.assertIn('matching: "fuzzy";', launcher.rofi_config(s, "x.rasi"))
        self.assertNotIn("match-mode", launcher.fuzzel_ini(s))


class Look(unittest.TestCase):
    def test_ini_keeps_other_lines(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "gtk-3.0" / "settings.ini"
            f.parent.mkdir()
            f.write_text("[Settings]\ngtk-font-name=Inter 11\ngtk-application-prefer-dark-theme=0\n", encoding="utf-8")
            appearance.apply("dark", Path(d), LOG)
            t = f.read_text(encoding="utf-8")
            self.assertIn("gtk-font-name=Inter 11", t)
            self.assertIn("gtk-application-prefer-dark-theme=1", t)
            self.assertEqual(t.count("prefer-dark-theme"), 1)
            self.assertIn("gtk-application-prefer-dark-theme=1", (Path(d) / "gtk-4.0" / "settings.ini").read_text())
            appearance.apply("light", Path(d), LOG)
            self.assertIn("gtk-application-prefer-dark-theme=0", f.read_text(encoding="utf-8"))
            self.assertTrue((Path(d) / "gtk-3.0" / "settings.ini.hyprstudio-original").is_file())


class MouseScroll(unittest.TestCase):
    def test_mouse_natural(self):
        s = model.hypr_state({"mouse_natural": True})
        self.assertRegex(model.hypr_conf(s), r"input \{[^}]*natural_scroll = (true|1)")
        self.assertRegex(model.hypr_lua(s), r"input = \{[^}]*natural_scroll\s*= true")


class Extract(unittest.TestCase):
    def test_traversal_and_links(self):
        import io
        import tarfile
        from hyprstudio import online
        buf = io.BytesIO()
        with tarfile.open(fileobj=buf, mode="w:gz") as tf:
            for name, data in (("T/index.theme", b"[Icon Theme]"), ("T/cursors/left_ptr", b"x"), ("../evil", b"x")):
                ti = tarfile.TarInfo(name)
                ti.size = len(data)
                tf.addfile(ti, io.BytesIO(data))
            for name, target in (("T/cursors/default", "left_ptr"), ("T/cursors/bad", "/etc/passwd")):
                ti = tarfile.TarInfo(name)
                ti.type = tarfile.SYMTYPE
                ti.linkname = target
                tf.addfile(ti)
        with tempfile.TemporaryDirectory() as d:
            dest = Path(d) / "x"
            dest.mkdir()
            online.safe_extract(buf.getvalue(), "a.tar.gz", dest)
            self.assertFalse((Path(d) / "evil").exists())
            self.assertTrue((dest / "T/cursors/default").exists())
            self.assertFalse((dest / "T/cursors/bad").exists())
            self.assertEqual([p.name for p in online.find_themes(dest)], ["T"])


class SuperAlone(unittest.TestCase):
    def test_release_flag(self):
        b = {"mods": ["SUPER"], "key": "SUPER_L", "action": "exec", "arg": "rofi -show drun", "flags": []}
        self.assertIn("bindr = SUPER, SUPER_L, exec, rofi -show drun", model.bind_conf(b))
        self.assertIn("release = true", model.bind_lua(b))
        b2 = dict(b, key="Q", flags=[])
        self.assertNotIn("release", model.bind_lua(b2))


class LauncherBinds(unittest.TestCase):
    LUA = ('local mainMod = "SUPER"\nlocal menu = "hyprlauncher"\n'
           'hl.bind(mainMod .. " + R", hl.dsp.exec_cmd(menu))\nhl.bind(mainMod .. " + Q", hl.dsp.exec_cmd("kitty"))\n')

    def test_detect_and_override(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.lua").write_text(self.LUA, encoding="utf-8")
            found = model.launcher_binds(h, [])
            self.assertEqual([(b["key"], b["arg"], w) for b, w in found], [("R", "hyprlauncher", "config")])
            own = [dict(found[0][0], arg="rofi -show drun")]
            self.assertEqual([w for _, w in model.launcher_binds(h, own)], ["own"])
            self.assertEqual(model.comment_conflicts(h, own, LOG), 1)
            self.assertIn('-- [Hypr Studio] hl.bind(mainMod .. " + R"', (h / "hyprland.lua").read_text(encoding="utf-8"))


class WallSearch(unittest.TestCase):
    def test_params_and_sfw(self):
        import json as _j
        from urllib.parse import parse_qs, urlparse
        from hyprstudio import online
        seen = {}

        def fake(url, timeout=0):
            seen.update({k: v[0] for k, v in parse_qs(urlparse(url).query).items()})
            return _j.dumps({"meta": {"last_page": 3}, "data": [
                {"id": "a", "purity": "sfw", "thumbs": {"small": "t"}, "path": "p/a.jpg", "resolution": "3840x2160",
                 "favorites": 5, "file_size": 1},
                {"id": "b", "purity": "sketchy", "thumbs": {"small": "t"}, "path": "p/b.jpg"}]}).encode()
        old, online._get = online._get, fake
        try:
            items, last = online.wall_search("berge", "toplist", "anime", "uhd")
        finally:
            online._get = old
        self.assertEqual([x["id"] for x in items], ["a"])
        self.assertEqual(last, 3)
        self.assertEqual((seen["purity"], seen["categories"], seen["atleast"], seen["q"]), ("100", "010", "3840x2160", "berge"))


class Accel(unittest.TestCase):
    def test_flat(self):
        self.assertRegex(model.hypr_lua(model.hypr_state({"accel": "flat"})), r'accel_profile\s*= "flat"')
        self.assertRegex(model.hypr_conf(model.hypr_state({"accel": "flat"})), r"accel_profile = flat")


class Remove(unittest.TestCase):
    def test_remove_command(self):
        from hyprstudio import packages
        self.assertEqual(packages.remove_command(["screenshot"], "pacman"),
                         ["pacman", "-Rs", "--noconfirm", "grim", "slurp", "wl-clipboard"])
        self.assertEqual(packages.remove_command(["kitty"], "apt"), ["apt-get", "remove", "-y", "kitty"])


class WaybarOnce(unittest.TestCase):
    LUA = ('hl.on("hyprland.start", function ()\n    hl.exec_cmd("waybar")\n    hl.exec_cmd("waybar & hyprpaper")\n'
           '    hl.exec_cmd("nm-applet")\nend)\n-- hl.exec_cmd("waybar")\n')

    def test_detect(self):
        only, chained = model.foreign_waybar_lines(self.LUA, "lua")
        self.assertEqual((only, chained), ([1], [2]))
        only, chained = model.foreign_waybar_lines("exec-once = waybar -c x\nexec-once = waybar & swaync\n# exec-once = waybar\n", "conf")
        self.assertEqual((only, chained), ([0], [1]))

    def test_once_and_managed(self):
        s = model.hypr_state({"autostart_waybar": True, "autostart": ["waybar", "nm-applet"]})
        self.assertEqual(model._autostart(s), [model.WAYBAR_ONCE, "nm-applet"])
        self.assertEqual(model._autostart(dict(s, autostart_waybar=False)), ["nm-applet"])
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.lua").write_text(self.LUA, encoding="utf-8")
            self.assertEqual(model.manage_waybar_autostart(h, dict(s, waybar_managed=False), LOG), 0)
            model.manage_waybar_autostart(h, dict(s, waybar_managed=True), LOG)
            txt = (h / "hyprland.lua").read_text(encoding="utf-8")
            self.assertIn('-- [Hypr Studio]     hl.exec_cmd("waybar")', txt)
            self.assertIn('    hl.exec_cmd("waybar & hyprpaper")', txt)
