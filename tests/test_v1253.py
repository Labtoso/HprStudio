import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import fixer, launcher, model  # noqa: E402

try:
    import lupa
except ImportError:  # optional: nur zum Ausführen der erzeugten Lua-Datei
    lupa = None

STUB = r"""
calls = {}
local function rec(path)
  return setmetatable({}, {
    __index = function(_, k) return rec(path .. "." .. k) end,
    __call = function(_, ...)
      calls[#calls + 1] = path
      for _, a in ipairs({...}) do if type(a) == "function" then a() end end
      return rec(path .. "()")
    end,
  })
end
hl = rec("hl")
"""
OFFICIAL = {"hl.config", "hl.curve", "hl.animation", "hl.env", "hl.on", "hl.exec_cmd", "hl.bind", "hl.monitor",
            "hl.window_rule", "hl.workspace_rule", "hl.gesture", "hl.dsp.exec_cmd", "hl.dsp.focus",
            "hl.dsp.window.close", "hl.dsp.window.move", "hl.dsp.window.float", "hl.dsp.window.fullscreen",
            "hl.dsp.window.pseudo", "hl.dsp.window.drag", "hl.dsp.window.resize", "hl.dsp.exit", "hl.dsp.layout",
            "hl.dsp.workspace.toggle_special"}


def full_state():
    b = model._bind
    return model.hypr_state({
        "binds": [b(["SUPER"], "R", "launcher", "rofi"), b(["SUPER"], "C", "close"), b(["SUPER"], "1", "workspace", "1"),
                  b(["SUPER"], "SUPER_L", "launcher", "llauncher", ["release"])],
        "autostart": ["nm-applet"], "autostart_waybar": True, "polkit_agent": True, "polkit_managed": True,
        "qt_theme": "kde", "cursor_theme": "Bibata", "smart_gaps": True, "gesture": 3, "monitor_on": True,
        "border_rotate": True})


class Apply(unittest.TestCase):
    def test_one_config_block_per_section(self):
        lua = model.hypr_lua(model.hypr_state(None))
        self.assertGreaterEqual(lua.count("hl.config({"), 6)
        head = lua.split("hl.curve")[0]  # nur die hl.config-Blöcke
        self.assertEqual(head.count("hl.config({"), head.count("\n})"))
        line = next(i for i, ln in enumerate(lua.splitlines(), 1) if ln.strip().startswith("xray"))
        self.assertEqual(fixer.option_path(lua, line), "decoration.blur.xray")

    @unittest.skipIf(lupa is None, "lupa nicht installiert")
    def test_lua_runs_and_uses_known_api(self):
        for s in (model.hypr_state(None), full_state()):
            rt = lupa.LuaRuntime()
            rt.execute(STUB)
            rt.execute(model.hypr_lua(s))
            used = set(rt.globals().calls.values())
            self.assertTrue(used <= OFFICIAL, used - OFFICIAL)

    def test_llauncher_json_backed_up_only_once(self):
        with tempfile.TemporaryDirectory() as d:
            home = Path(d)
            s = launcher.state({"app": "llauncher"})
            for _ in range(3):
                launcher.apply(s, home, lambda *_: None)
            backups = [p.name for p in (home / "LabtosoStudios").iterdir() if ".hyprstudio-" in p.name]
            self.assertEqual(backups, [])
            data = json.loads((home / "LabtosoStudios" / "l-launcher.json").read_text(encoding="utf-8"))
            self.assertEqual(launcher.state(data)["app"], "llauncher")


if __name__ == "__main__":
    unittest.main()
