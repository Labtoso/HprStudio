import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from hyprstudio import model  # noqa: E402


def strip_comment(text: str) -> str:
    return "\n".join(ln for ln in text.splitlines() if not ln.startswith("//"))


class Colors(unittest.TestCase):
    def test_norm(self):
        self.assertEqual(model.norm("#abc"), "#aabbccff")
        self.assertEqual(model.norm("33CCFF"), "#33ccffff")
        self.assertEqual(model.norm("#33ccffee"), "#33ccffee")
        self.assertEqual(model.norm("kaputt"), "#000000ff")
        self.assertEqual(model.rgba_hypr("#33ccffee"), "rgba(33ccffee)")
        self.assertEqual(model.rgba_css("#ff000080"), "rgba(255, 0, 0, 0.50)")


class Hypr(unittest.TestCase):
    def test_all_presets_render(self):
        for name in model.HYPR_PRESETS:
            s = model.preset_state(name)
            lua, conf = model.hypr_lua(s), model.hypr_conf(s)
            self.assertEqual(lua.count("{"), lua.count("}"), name)
            self.assertEqual(conf.count("{"), conf.count("}"), name)
            self.assertIn("hl.config({", lua)

    def test_lua_like_example(self):
        lua = " ".join(model.hypr_lua(model.hypr_state(None)).split())
        self.assertIn('active_border = { colors = {"rgba(33ccffee)", "rgba(00ff99ee)"}, angle = 45 }', lua)
        self.assertIn("noise = 0.0117,", lua)
        self.assertIn('hl.curve("hs_curve", { type = "bezier", points = { {0.23, 1.0}, {0.32, 1.0} } })', lua)
        self.assertIn('hl.animation({ leaf = "windowsIn", enabled = true, speed = 4.1, bezier = "hs_curve", '
                      'style = "popin 80%" })', lua)
        self.assertIn("natural_scroll = false", lua)

    def test_conf(self):
        conf = model.hypr_conf(model.hypr_state(None))
        self.assertIn("col.active_border = rgba(33ccffee) rgba(00ff99ee) 45deg", conf)
        self.assertIn("bezier = hs_curve, 0.23, 1.0, 0.32, 1.0", conf)
        self.assertIn("animation = windowsIn, 1, 4.1, hs_curve, popin 80%", conf)

    def test_no_anim(self):
        s = model.preset_state("minimal")
        self.assertNotIn("hl.curve", model.hypr_lua(s))
        self.assertIn('active_border = "rgba(3d8bfdff)"', " ".join(model.hypr_lua(s).split()))

    def test_state_types(self):
        s = model.hypr_state({"gaps_in": 7, "blur_vibrancy": 1, "gaps_out": "x", "unbekannt": 1, "rounding": True})
        self.assertEqual(s["gaps_in"], 7)
        self.assertEqual(s["blur_vibrancy"], 1.0)
        self.assertEqual(s["gaps_out"], 20)
        self.assertEqual(s["rounding"], 10)
        self.assertNotIn("unbekannt", s)

    def _apply(self, fmt):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            main = h / f"hyprland.{fmt}"
            main.write_text("# meine config\n", encoding="utf-8")
            logs = []
            s = model.hypr_state(None)
            ok, got = model.apply_hypr(s, h, logs.append)
            self.assertTrue(ok)
            self.assertEqual(got, fmt)
            s["gaps_in"] = 9
            model.apply_hypr(s, h, logs.append)
            text = main.read_text(encoding="utf-8")
            self.assertEqual(text.count(model.INCLUDE[fmt][0]), 1)
            self.assertTrue((h / f"hyprland.{fmt}.hyprstudio-original").is_file())
            own = h / f"hyprstudio.{fmt}"
            self.assertIn("9", own.read_text(encoding="utf-8"))
            self.assertTrue(model.undo_hypr(h, logs.append))
            self.assertIn("gaps_in", own.read_text(encoding="utf-8"))
            self.assertNotIn("gaps_in          = 9", own.read_text(encoding="utf-8"))
            self.assertNotIn("gaps_in = 9", own.read_text(encoding="utf-8"))

    def test_apply_lua(self):
        self._apply("lua")

    def test_apply_conf(self):
        self._apply("conf")

    def test_lua_wins(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.conf").write_text("", encoding="utf-8")
            self.assertEqual(model.hypr_format(h), "conf")
            (h / "hyprland.lua").write_text("", encoding="utf-8")
            self.assertEqual(model.hypr_format(h), "lua")


EXAMPLE = '''local terminal    = "kitty"
local mainMod = "SUPER" -- Sets "Windows" key as main modifier
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal))
local closeWindowBind = hl.bind(mainMod .. " + C", hl.dsp.window.close())
-- hl.bind(mainMod .. " + E", hl.dsp.exec_cmd(fileManager))
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
for i = 1, 10 do
    local key = i % 10
    hl.bind(mainMod .. " + " .. key,             hl.dsp.focus({ workspace = i}))
end
hl.bind("XF86AudioMute",        hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"),     { locked = true })
'''


class HyprExtras(unittest.TestCase):
    def test_extras(self):
        s = model.hypr_state({"smart_gaps": True, "gesture": 3, "autostart": ["nm-applet", ""],
                              "autostart_waybar": True, "monitor_on": True, "monitor_scale": "1.25",
                              "border_rotate": True, "anim_fade": False, "cursor_theme": "Bibata"})
        lua, conf = model.hypr_lua(s), model.hypr_conf(s)
        for x in ('hl.workspace_rule({ workspace = "w[tv1]", gaps_out = 0, gaps_in = 0 })',
                  'hl.gesture({ fingers = 3, direction = "horizontal", action = "workspace" })',
                  'hl.on("hyprland.start", function ()\n    hl.exec_cmd("pgrep -x waybar >/dev/null || waybar")\n    hl.exec_cmd("nm-applet")\nend)',
                  "    scale    = 1.25,", 'hl.animation({ leaf = "fade", enabled = false })',
                  'hl.animation({ leaf = "borderangle", enabled = true, speed = 60.0, bezier = "hs_linear", style = "loop" })',
                  'hl.env("XCURSOR_THEME", "Bibata")'):
            self.assertIn(x, lua)
        for x in ("workspace = w[tv1], gapsout:0, gapsin:0", "gesture = 3, horizontal, workspace",
                  "exec-once = pgrep -x waybar >/dev/null || waybar", "exec-once = nm-applet", "monitor = , preferred, auto, 1.25",
                  "animation = fade, 0", "animation = borderangle, 1, 60.0, hs_linear, loop",
                  "    col.active_border = rgba(33ccffee) rgba(00ff99ee) 45deg", "    touchpad {"):
            self.assertIn(x, conf)
        self.assertEqual(conf.count("{"), conf.count("}"))
        self.assertNotIn("fadeIn", lua)

    def test_preset_keeps_behaviour(self):
        base = model.hypr_state({"kb_layout": "us", "layout": "master", "gaps_in": 30})
        s = model.preset_state("nord", base)
        self.assertEqual(s["kb_layout"], "us")
        self.assertEqual(s["layout"], "master")
        self.assertEqual(s["gaps_in"], 4)


class Binds(unittest.TestCase):
    def test_lua_and_conf(self):
        s = model.hypr_state({"binds": model.default_binds() + model.TEMPLATES["screenshot"] + model.TEMPLATES["media"]})
        lua, conf = model.hypr_lua(s), model.hypr_conf(s)
        self.assertIn('hl.bind("SUPER + Q", hl.dsp.exec_cmd("kitty"))', lua)
        self.assertIn('hl.bind("SUPER + C", hl.dsp.window.close())', lua)
        self.assertIn('hl.bind("SUPER + SHIFT + 3", hl.dsp.window.move({ workspace = 3 }))', lua)
        self.assertIn('hl.bind("SUPER + left", hl.dsp.focus({ direction = "left" }))', lua)
        self.assertIn('hl.bind("Print", hl.dsp.exec_cmd("grim -g \\"$(slurp)\\" - | wl-copy"))', lua)
        self.assertIn("unbind = SUPER, Q\nbind = SUPER, Q, exec, kitty", conf)
        self.assertIn("bind = SUPER SHIFT, 3, movetoworkspace, 3", conf)
        self.assertIn("bind = SUPER, left, movefocus, l", conf)
        self.assertIn('hl.bind("SUPER + mouse:272", hl.dsp.window.drag(), { mouse = true })', lua)
        self.assertIn('hl.dsp.exec_cmd("wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle"), { locked = true, repeating = true })', lua)
        self.assertIn("bindm = SUPER, mouse:272, movewindow", conf)
        self.assertIn("bindle = , XF86AudioMute, exec, wpctl set-mute @DEFAULT_AUDIO_SINK@ toggle", conf)

    def test_empty_writes_nothing(self):
        s = model.hypr_state(None)
        self.assertNotIn("hl.bind", model.hypr_lua(s))
        self.assertNotIn("bind =", model.hypr_conf(s))

    def test_invalid_skipped(self):
        s = model.hypr_state({"binds": [{"mods": ["SUPER"], "key": "", "action": "exec", "arg": "kitty"},
                                        {"mods": ["SUPER"], "key": "T", "action": "exec", "arg": ""},
                                        {"mods": ["SUPER"], "key": "T", "action": "nope", "arg": ""}]})
        self.assertEqual(len(s["binds"]), 2)
        self.assertNotIn("hl.bind", model.hypr_lua(s))

    def test_parse_example(self):
        combos = [c for _, c in model.lua_bind_combos(EXAMPLE)]
        self.assertIn((("SUPER",), "q"), combos)
        self.assertIn((("SUPER",), "c"), combos)
        self.assertIn((("SUPER",), "left"), combos)
        self.assertIn(((), "xf86audiomute"), combos)
        self.assertNotIn((("SUPER",), "e"), combos)  # auskommentiert
        self.assertEqual(len(combos), 4)  # Schleife mit Variable wird übersprungen

    def test_comment_conflicts(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.lua").write_text(EXAMPLE, encoding="utf-8")
            n = model.comment_conflicts(h, [{"mods": ["SUPER"], "key": "q", "action": "exec", "arg": "foot"}], print)
            self.assertEqual(n, 1)
            text = (h / "hyprland.lua").read_text(encoding="utf-8")
            self.assertIn('-- [Hypr Studio] hl.bind(mainMod .. " + Q"', text)
            self.assertIn('local closeWindowBind = hl.bind(mainMod .. " + C"', text)
            self.assertEqual(len(list(h.glob("hyprland.lua.hyprstudio-*"))), 1)


FULL_LUA = '''local terminal    = "kitty"
local fileManager = "dolphin"
local mainMod = "SUPER" -- Sets "Windows" key as main modifier
hl.bind(mainMod .. " + Q", hl.dsp.exec_cmd(terminal))
local closeWindowBind = hl.bind(mainMod .. " + C", hl.dsp.window.close())
hl.bind(mainMod .. " + M", hl.dsp.exec_cmd("command -v hyprshutdown >/dev/null 2>&1 && hyprshutdown || hyprctl dispatch 'hl.dsp.exit()'"))
hl.bind(mainMod .. " + V", hl.dsp.window.float({ action = "toggle" }))
hl.bind(mainMod .. " + J", hl.dsp.layout("togglesplit"))    -- dwindle only
hl.bind(mainMod .. " + left",  hl.dsp.focus({ direction = "left" }))
for i = 1, 10 do
    local key = i % 10 -- 10 maps to key 0
    hl.bind(mainMod .. " + " .. key,             hl.dsp.focus({ workspace = i}))
    hl.bind(mainMod .. " + SHIFT + " .. key,     hl.dsp.window.move({ workspace = i }))
end
hl.bind(mainMod .. " + S",         hl.dsp.workspace.toggle_special("magic"))
hl.bind(mainMod .. " + SHIFT + S", hl.dsp.window.move({ workspace = "special:magic" }))
hl.bind(mainMod .. " + mouse_down", hl.dsp.focus({ workspace = "e+1" }))
hl.bind(mainMod .. " + mouse:272", hl.dsp.window.drag(),   { mouse = true })
hl.bind("XF86AudioRaiseVolume", hl.dsp.exec_cmd("wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+"), { locked = true, repeating = true })
hl.bind(mainMod .. " + X", function() hl.dispatch(hl.dsp.exit()) end)
'''

CONF = """$mainMod = SUPER
$terminal = kitty
bind = $mainMod, Q, exec, $terminal
bind = $mainMod, C, killactive,
bind = $mainMod SHIFT, 3, movetoworkspace, 3
bind = $mainMod, mouse_down, workspace, e+1
bindm = $mainMod, mouse:272, movewindow
bindel = ,XF86AudioRaiseVolume, exec, wpctl set-volume -l 1 @DEFAULT_AUDIO_SINK@ 5%+
bind = $mainMod, Z, sendshortcut, CTRL, C
"""


class Import(unittest.TestCase):
    def test_lua(self):
        binds, idx = model.import_lua(FULL_LUA)
        by = {model.combo_text(b): b for b in binds}
        self.assertEqual(by["SUPER + Q"]["arg"], "kitty")
        self.assertEqual(by["SUPER + C"]["action"], "close")
        self.assertIn("hyprshutdown", by["SUPER + M"]["arg"])
        self.assertEqual(by["SUPER + 0"], {"mods": ["SUPER"], "key": "0", "action": "workspace", "arg": "10", "flags": []})
        self.assertEqual(by["SUPER + SHIFT + 3"]["action"], "movetows")
        self.assertEqual(by["SUPER + SHIFT + S"]["action"], "movespecial")
        self.assertEqual(by["SUPER + mouse_down"]["action"], "wsnext")
        self.assertEqual(by["SUPER + mouse:272"]["action"], "drag")
        self.assertEqual(by["XF86AudioRaiseVolume"]["flags"], ["locked", "repeating"])
        self.assertNotIn("SUPER + X", by)  # Lua-Funktion bleibt in der Config
        self.assertEqual(len(binds), 31)
        lines = FULL_LUA.splitlines()
        self.assertNotIn(len(lines) - 1, idx)
        self.assertIn(9, idx)   # for-Zeile
        self.assertIn(13, idx)  # end
        self.assertNotIn(0, idx)

    def test_roundtrip(self):
        binds, _ = model.import_lua(FULL_LUA)
        lua = "\n".join(model.bind_lua(b) for b in binds)
        again, _ = model.import_lua(lua)
        self.assertEqual(binds, again)

    def test_conf(self):
        binds, idx = model.import_conf(CONF)
        by = {model.combo_text(b): b for b in binds}
        self.assertEqual(by["SUPER + Q"]["arg"], "kitty")
        self.assertEqual(by["SUPER + SHIFT + 3"]["action"], "movetows")
        self.assertEqual(by["SUPER + mouse_down"]["action"], "wsnext")
        self.assertEqual(by["SUPER + mouse:272"]["action"], "drag")
        self.assertEqual(by["XF86AudioRaiseVolume"]["flags"], ["locked", "repeating"])
        self.assertEqual(len(binds), 6)
        self.assertEqual(idx, [2, 3, 4, 5, 6, 7])

    def test_import_comments_out(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.lua").write_text(FULL_LUA, encoding="utf-8")
            binds = model.import_binds(h, lambda *_: None)
            text = (h / "hyprland.lua").read_text(encoding="utf-8")
            self.assertEqual(len(binds), 31)
            self.assertIn("-- [Hypr Studio] for i = 1, 10 do", text)
            self.assertIn('hl.bind(mainMod .. " + X", function()', text.split("-- [Hypr Studio]")[-1])
            self.assertEqual(model.import_lua(text)[0], [])


class Waybar(unittest.TestCase):
    def test_presets_json(self):
        for name in model.WAYBAR_PRESETS:
            s = model.waybar_preset(name)
            cfg = json.loads(strip_comment(model.waybar_json(s)))
            self.assertEqual(cfg["position"], s["position"])
            for m in cfg["modules-left"] + cfg["modules-center"] + cfg["modules-right"]:
                self.assertIn(m, cfg)
            css = model.waybar_css(s)
            self.assertEqual(css.count("{"), css.count("}"), name)

    def test_options(self):
        s = model.waybar_state({"ws_format": "dot", "ws_persist": 5, "colorful": True, "clock_fmt": "hms",
                                "tooltips": False, "net_fmt": "ip", "ws_look": "underline", "layer": "bottom",
                                "left": ["hyprland/workspaces", "mpris"], "right": ["clock", "network", "custom/power"]})
        cfg = json.loads(strip_comment(model.waybar_json(s)))
        self.assertEqual(cfg["hyprland/workspaces"]["persistent-workspaces"], {"*": 5})
        self.assertEqual(cfg["hyprland/workspaces"]["format"], "{icon}")
        self.assertEqual(cfg["clock"]["interval"], 1)
        self.assertFalse(cfg["clock"]["tooltip"])
        self.assertIn("{ipaddr}", cfg["network"]["format-wifi"])
        self.assertEqual(cfg["layer"], "bottom")
        self.assertEqual(cfg["custom/power"]["on-click"], "wlogout")
        css = model.waybar_css(s)
        self.assertIn("#clock { color: rgba(", css)
        self.assertIn("box-shadow: inset 0 -3px", css)

    def test_preset_keeps_options(self):
        base = model.waybar_state({"font": "Inter", "clock_fmt": "full", "bg": "#ff0000ff"})
        s = model.waybar_preset("islands", base)
        self.assertEqual((s["font"], s["clock_fmt"], s["style"]), ("Inter", "full", "islands"))
        self.assertEqual(s["bg"], "#151c26ee")

    def test_state_filters_unknown_modules(self):
        s = model.waybar_state({"left": ["clock", "nix"], "height": "hoch"})
        self.assertEqual(s["left"], ["clock"])
        self.assertEqual(s["height"], 34)

    def test_apply_backs_up_foreign(self):
        with tempfile.TemporaryDirectory() as d:
            w = Path(d)
            (w / "config").write_text('{"meins": 1}', encoding="utf-8")
            (w / "style.css").write_text("* {}", encoding="utf-8")
            logs = []
            model.apply_waybar(model.waybar_state(None), w, logs.append)
            self.assertEqual((w / "config.hyprstudio-original").read_text(encoding="utf-8"), '{"meins": 1}')
            self.assertTrue((w / "style.css.hyprstudio-original").is_file())
            self.assertIn(model.MARK, (w / "config").read_text(encoding="utf-8"))
            s = model.waybar_state(None)
            s["height"] = 40
            model.apply_waybar(s, w, logs.append)
            self.assertTrue((w / "config.bak").is_file())
            self.assertTrue(model.undo_waybar(w, logs.append))
            self.assertIn('"height": 34', (w / "config").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()


class Workspaces(unittest.TestCase):
    def test_rules(self):
        ws = model.default_workspaces()
        ws[0].update(name="Web", monitor="DP-1", default=True, gaps_out=0)
        ws[1].update(persistent=True, border=4, no_rounding=True)
        s = model.hypr_state({"workspaces_on": True, "workspaces": ws})
        lua, conf = model.hypr_lua(s), model.hypr_conf(s)
        self.assertIn('hl.workspace_rule({ workspace = "1", default_name = "Web", monitor = "DP-1", default = true, '
                      'gaps_out = 0 })', lua)
        self.assertIn('hl.workspace_rule({ workspace = "2", persistent = true, border_size = 4, no_rounding = true })', lua)
        self.assertNotIn('workspace = "3"', lua)
        self.assertIn("workspace = 1, defaultName:Web, monitor:DP-1, default:true, gapsout:0", conf)
        s["workspaces_on"] = False
        self.assertNotIn("Arbeitsflächen", model.hypr_lua(s))

    def test_clean(self):
        ws = model.clean_workspaces([{"id": 3, "name": " A "}, {"id": 3}, {"id": 99}, "x", {"id": 1, "gaps_in": "x"}])
        self.assertEqual([w["id"] for w in ws], [1, 3])
        self.assertEqual(ws[1]["name"], "A")
        self.assertEqual(ws[0]["gaps_in"], -1)


class FormatSwitch(unittest.TestCase):
    def tearDown(self):
        model.FORMAT = ""

    def test_forced_format(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.lua").write_text("-- x\n", encoding="utf-8")
            (h / "hyprland.conf").write_text("# x\n", encoding="utf-8")
            self.assertEqual(model.hypr_format(h), "lua")
            model.FORMAT = "conf"
            self.assertEqual(model.hypr_format(h), "conf")
            dry, model.DRY = model.DRY, False
            try:
                ok, fmt = model.apply_hypr(model.hypr_state(None), h, lambda *_: None)
            finally:
                model.DRY = dry
            self.assertTrue(ok)
            self.assertTrue((h / "hyprstudio.conf").is_file())
            self.assertIn("source = ~/.config/hypr/hyprstudio.conf", (h / "hyprland.conf").read_text(encoding="utf-8"))

    def test_forced_missing_main(self):
        with tempfile.TemporaryDirectory() as d:
            h = Path(d)
            (h / "hyprland.conf").write_text("# x\n", encoding="utf-8")
            model.FORMAT = "lua"
            dry, model.DRY = model.DRY, False
            try:
                self.assertEqual(model.apply_hypr(model.hypr_state(None), h, lambda *_: None), (False, "nomain.lua"))
            finally:
                model.DRY = dry
