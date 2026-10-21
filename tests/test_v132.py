import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import appearance, model  # noqa: E402

try:
    import lupa
except ImportError:
    lupa = None


class DarkEverywhere(unittest.TestCase):
    def test_portals_conf(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            self.assertTrue(appearance.write_portals_conf(home, lambda *_: None))
            text = (home / "xdg-desktop-portal" / "hyprland-portals.conf").read_text(encoding="utf-8")
            self.assertIn("default=hyprland;gtk", text)
            self.assertIn("org.freedesktop.impl.portal.Settings=gtk", text)
            own = home / "xdg-desktop-portal" / "hyprland-portals.conf"
            own.write_text("[preferred]\ndefault=gtk\n", encoding="utf-8")
            self.assertFalse(appearance.write_portals_conf(home, lambda *_: None))  # eigene Datei bleibt
            self.assertEqual(own.read_text(encoding="utf-8"), "[preferred]\ndefault=gtk\n")

    def test_env_file_and_include(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            (home / "hypr").mkdir()
            (home / "hypr" / "hyprland.lua").write_text("-- meins\n", encoding="utf-8")
            old, model.FORMAT = model.FORMAT, "lua"
            try:
                self.assertTrue(appearance.apply_env("dark", home, lambda *_: None))
                appearance.apply_env("dark", home, lambda *_: None)
            finally:
                model.FORMAT = old
            look = (home / "hypr" / "hyprstudio_look.lua").read_text(encoding="utf-8")
            self.assertIn('hl.env("GTK_THEME", "Adwaita:dark")', look)
            self.assertEqual((home / "hypr" / "hyprland.lua").read_text(encoding="utf-8").count('require("hyprstudio_look")'), 1)
        self.assertIn("env = GTK_THEME,Adwaita\n", appearance.env_content("light", "", "conf"))

    @unittest.skipIf(lupa is None, "lupa nicht installiert")
    def test_lua_runs(self):
        rt = lupa.LuaRuntime()
        rt.execute("calls={} local function r(p) return setmetatable({}, {__index=function(_,k) return r(p..'.'..k) end,"
                   "__call=function(_, ...) calls[#calls+1]=p for _,a in ipairs({...}) do if type(a)=='function' then a() end end"
                   " return r(p..'()') end}) end hl=r('hl')")
        rt.execute(appearance.env_content("dark", "kde", "lua"))
        self.assertEqual(set(rt.globals().calls.values()), {"hl.env", "hl.on", "hl.exec_cmd"})


if __name__ == "__main__":
    unittest.main()
