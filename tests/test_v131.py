import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import model, perf  # noqa: E402

try:
    import lupa
except ImportError:
    lupa = None


class Performance(unittest.TestCase):
    def test_content(self):
        on = perf.perf_state({"portal_env": True, "light": True})
        lua = perf.content(on, "lua")
        self.assertIn('hl.exec_cmd("dbus-update-activation-environment --systemd --all")', lua)
        self.assertIn("shadow = { enabled = false }", lua)
        conf = perf.content(on, "conf")
        self.assertIn("exec-once = dbus-update-activation-environment --systemd --all", conf)
        self.assertIn("passes = 1", conf)
        self.assertIn("nichts eingeschaltet", perf.content(perf.perf_state(None), "lua"))

    @unittest.skipIf(lupa is None, "lupa nicht installiert")
    def test_lua_runs(self):
        rt = lupa.LuaRuntime()
        rt.execute("calls={} local function r(p) return setmetatable({}, {__index=function(_,k) return r(p..'.'..k) end,"
                   "__call=function(_, ...) calls[#calls+1]=p for _,a in ipairs({...}) do if type(a)=='function' then a() end end"
                   " return r(p..'()') end}) end hl=r('hl')")
        rt.execute(perf.content(perf.perf_state({"portal_env": True, "light": True}), "lua"))
        self.assertEqual(set(rt.globals().calls.values()), {"hl.on", "hl.exec_cmd", "hl.config"})

    def test_write_includes_once(self):
        with tempfile.TemporaryDirectory() as d:
            hdir = Path(d)
            (hdir / "hyprland.lua").write_text("-- meins\n", encoding="utf-8")
            old, model.FORMAT = model.FORMAT, "lua"
            try:
                ps = perf.perf_state({"light": True})
                self.assertTrue(perf.write(hdir, ps, lambda *_: None))
                self.assertTrue(perf.write(hdir, ps, lambda *_: None))
            finally:
                model.FORMAT = old
            main = (hdir / "hyprland.lua").read_text(encoding="utf-8")
            self.assertEqual(main.count('require("hyprstudio_perf")'), 1)
            self.assertTrue((hdir / "hyprstudio_perf.lua").is_file())

    def test_commands(self):
        z = perf.zram_command("pacman")
        self.assertEqual(z[:2], ["sh", "-c"])
        self.assertIn("zram-generator", z[2])
        self.assertIn("[ -f /etc/systemd/zram-generator.conf ] ||", z[2])  # vorhandene Einstellung bleibt
        self.assertIn("xdg-desktop-portal-gtk", perf.portal_command("pacman"))
        self.assertEqual(perf.zram_command(None), [])


if __name__ == "__main__":
    unittest.main()
