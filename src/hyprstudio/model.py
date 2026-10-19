"""Daten, Presets und Config-Erzeugung für Hyprland (Lua ab 0.55 oder hyprlang) und Waybar. Ohne Qt."""

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

MARK = "Hypr Studio (LabtosoStudios)"
DRY = os.environ.get("HYPRSTUDIO_DRYRUN") == "1" or sys.platform == "win32"
CACHE = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache")) / "LabtosoStudios" / "hyprstudio"


def config_home() -> Path:
    if DRY:
        return CACHE / "testmodus" / ".config"
    return Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))


# ---------- Farben ----------

def norm(c: str) -> str:
    """'#rgb', '#rrggbb' oder '#rrggbbaa' → '#rrggbbaa' (klein)."""
    h = c.strip().lstrip("#").lower()
    if len(h) == 3:
        h = "".join(ch * 2 for ch in h)
    if len(h) == 6:
        h += "ff"
    if len(h) != 8 or any(ch not in "0123456789abcdef" for ch in h):
        return "#000000ff"
    return "#" + h


def rgba_hypr(c: str) -> str:
    return f"rgba({norm(c)[1:]})"


def rgba_css(c: str, alpha: float | None = None) -> str:
    h = norm(c)[1:]
    r, g, b, a = (int(h[i:i + 2], 16) for i in (0, 2, 4, 6))
    a = a / 255 if alpha is None else alpha
    return f"rgba({r}, {g}, {b}, {a:.2f})"


# ---------- Hyprland ----------

HYPR_DEFAULT = {
    "gaps_in": 5, "gaps_out": 20, "border_size": 2, "layout": "dwindle",
    "gradient": True, "active1": "#33ccffee", "active2": "#00ff99ee", "angle": 45,
    "inactive": "#595959aa",
    "rounding": 10, "rounding_power": 2.0,
    "active_opacity": 1.0, "inactive_opacity": 1.0, "dim_inactive": False, "dim_strength": 0.3,
    "blur": True, "blur_size": 3, "blur_passes": 1, "blur_vibrancy": 0.17,
    "shadow": True, "shadow_range": 4, "shadow_power": 3, "shadow_color": "#1a1a1aee",
    "anim": True, "anim_curve": "smooth", "anim_tempo": 1.0, "win_style": "popin", "ws_style": "slide",
    "kb_layout": "de", "sensitivity": 0.0, "follow_mouse": 1, "natural_scroll": False, "no_logo": True,
    "binds": [],  # leer = Hypr Studio schreibt keine Tastenkürzel
}

HYPR_PRESETS = {
    "hyprland": {},
    "tokyo": {"active1": "#7aa2f7ff", "active2": "#bb9af7ff", "inactive": "#414868aa", "gaps_in": 5,
              "gaps_out": 12, "rounding": 10, "inactive_opacity": 0.92, "blur_size": 6, "blur_passes": 2},
    "catppuccin": {"active1": "#cba6f7ff", "active2": "#89b4faff", "inactive": "#45475aaa", "rounding": 12,
                   "gaps_out": 14, "inactive_opacity": 0.94},
    "nord": {"active1": "#88c0d0ff", "active2": "#81a1c1ff", "inactive": "#4c566aaa", "rounding": 8,
             "gaps_in": 4, "gaps_out": 10, "anim_curve": "fast"},
    "gruvbox": {"active1": "#fabd2fff", "active2": "#fe8019ff", "inactive": "#504945aa", "rounding": 4,
                "gaps_in": 4, "gaps_out": 8, "border_size": 3, "angle": 90},
    "rosepine": {"active1": "#ebbcbaff", "active2": "#c4a7e7ff", "inactive": "#26233aaa", "rounding": 14,
                 "gaps_out": 16, "anim_curve": "bouncy"},
    "dracula": {"active1": "#bd93f9ff", "active2": "#ff79c6ff", "inactive": "#44475aaa", "rounding": 10,
                "angle": 135},
    "glass": {"gradient": False, "active1": "#ffffff66", "inactive": "#ffffff22", "rounding": 18, "gaps_in": 8,
              "gaps_out": 22, "active_opacity": 0.9, "inactive_opacity": 0.78, "blur_size": 8, "blur_passes": 3,
              "blur_vibrancy": 0.3, "shadow_range": 18, "anim_curve": "bouncy"},
    "minimal": {"gradient": False, "active1": "#3d8bfdff", "inactive": "#2a2f38ff", "border_size": 1,
                "gaps_in": 0, "gaps_out": 0, "rounding": 0, "blur": False, "shadow": False, "anim": False},
}

CURVES = {
    "smooth": ((0.23, 1.0), (0.32, 1.0)),
    "fast": ((0.15, 0.0), (0.1, 1.0)),
    "bouncy": ((0.34, 1.56), (0.64, 1.0)),
    "linear": ((0.0, 0.0), (1.0, 1.0)),
}
# Grund-Dauer in Dezisekunden (wie im Hyprland-Beispiel)
ANIMS = (
    ("windowsIn", 4.1, "win"), ("windowsOut", 1.5, "win"), ("windowsMove", 4.8, None),
    ("border", 5.4, None), ("fade", 3.0, None), ("layers", 3.8, None), ("workspaces", 3.0, "ws"),
)
WIN_STYLES = {"popin": "popin 80%", "slide": "slide", "gnomed": "gnomed"}
WS_STYLES = {"slide": "slide", "slidevert": "slidevert", "fade": "fade", "slidefade": "slidefade 20%"}


def hypr_state(saved: dict | None) -> dict:
    s = dict(HYPR_DEFAULT)
    s["binds"] = []
    for k, v in (saved or {}).items():
        if k not in s:
            continue
        if k == "binds":
            s[k] = clean_binds(v)
        elif type(v) is type(s[k]):
            s[k] = v
        elif isinstance(s[k], float) and type(v) is int:
            s[k] = float(v)
    return s


def preset_state(name: str) -> dict:
    s = dict(HYPR_DEFAULT)
    s["binds"] = []
    s.update(HYPR_PRESETS.get(name, {}))
    return s


# ---------- Tastenkürzel ----------

MODS = ("SUPER", "SHIFT", "CTRL", "ALT")
MOD_ALIAS = {"SUPER": "SUPER", "WIN": "SUPER", "MOD4": "SUPER", "META": "SUPER", "LOGO": "SUPER",
             "SHIFT": "SHIFT", "CTRL": "CTRL", "CONTROL": "CTRL", "ALT": "ALT", "MOD1": "ALT"}
# Aktion → braucht Argument?
ACTIONS = {
    "exec": True, "close": False, "fullscreen": False, "float": False, "focus": True,
    "workspace": True, "movetows": True, "special": False, "togglesplit": False,
}
DIRECTIONS = ("left", "right", "up", "down")
EXEC_SUGGEST = ("kitty", "dolphin", "nautilus", "firefox", "rofi -show drun", "wofi --show drun", "hyprlauncher",
                "hyprlock", 'grim -g "$(slurp)" - | wl-copy', "pavucontrol", "code")


def clean_binds(v) -> list:
    out = []
    if not isinstance(v, list):
        return out
    for b in v:
        if not isinstance(b, dict):
            continue
        mods = [m for m in MODS if m in (b.get("mods") or [])]
        key = str(b.get("key") or "").strip()
        act = b.get("action")
        if act not in ACTIONS:
            continue
        out.append({"mods": mods, "key": key, "action": act, "arg": str(b.get("arg") or "").strip()})
    return out


def default_binds() -> list:
    b = [
        (["SUPER"], "Q", "exec", "kitty"), (["SUPER"], "C", "close", ""), (["SUPER"], "E", "exec", "dolphin"),
        (["SUPER"], "R", "exec", "rofi -show drun"), (["SUPER"], "V", "float", ""), (["SUPER"], "F", "fullscreen", ""),
        (["SUPER"], "J", "togglesplit", ""), (["SUPER"], "L", "exec", "hyprlock"),
        ([], "Print", "exec", 'grim -g "$(slurp)" - | wl-copy'), (["SUPER"], "S", "special", ""),
    ]
    b += [(["SUPER"], d, "focus", d) for d in DIRECTIONS]
    b += [(["SUPER"], str(i), "workspace", str(i)) for i in range(1, 6)]
    b += [(["SUPER", "SHIFT"], str(i), "movetows", str(i)) for i in range(1, 6)]
    return [{"mods": m, "key": k, "action": a, "arg": g} for m, k, a, g in b]


def combo(mods, key: str) -> tuple:
    return tuple(sorted({MOD_ALIAS.get(m.upper(), m.upper()) for m in mods})), key.strip().lower()


def combo_text(b: dict) -> str:
    return " + ".join([*b["mods"], b["key"]])


def bind_ok(b: dict) -> bool:
    if not b["key"]:
        return False
    if ACTIONS[b["action"]] and not b["arg"]:
        return False
    if b["action"] == "focus" and b["arg"] not in DIRECTIONS:
        return False
    return True


def _ws(arg: str) -> str:
    return arg if arg.lstrip("-").isdigit() else _lua_str(arg)


def bind_lua(b: dict) -> str:
    a, g = b["action"], b["arg"]
    dsp = {
        "exec": lambda: f"hl.dsp.exec_cmd({_lua_str(g)})",
        "close": lambda: "hl.dsp.window.close()",
        "fullscreen": lambda: 'hl.dsp.window.fullscreen({ action = "toggle" })',
        "float": lambda: 'hl.dsp.window.float({ action = "toggle" })',
        "focus": lambda: f'hl.dsp.focus({{ direction = "{g}" }})',
        "workspace": lambda: f"hl.dsp.focus({{ workspace = {_ws(g)} }})",
        "movetows": lambda: f"hl.dsp.window.move({{ workspace = {_ws(g)} }})",
        "special": lambda: 'hl.dsp.workspace.toggle_special("magic")',
        "togglesplit": lambda: 'hl.dsp.layout("togglesplit")',
    }[a]()
    return f"hl.bind({_lua_str(combo_text(b))}, {dsp})"


def bind_conf(b: dict) -> list:
    a, g = b["action"], b["arg"]
    d = {"exec": f"exec, {g}", "close": "killactive,", "fullscreen": "fullscreen, 0", "float": "togglefloating,",
         "focus": f"movefocus, {g[:1]}", "workspace": f"workspace, {g}", "movetows": f"movetoworkspace, {g}",
         "special": "togglespecialworkspace, magic", "togglesplit": "togglesplit,"}[a]
    mods = " ".join(b["mods"])
    # unbind entfernt vorher gesetzte Kürzel mit derselben Taste (aus hyprland.conf)
    return [f"unbind = {mods}, {b['key']}", f"bind = {mods}, {b['key']}, {d}"]


def _split_args(s: str) -> str:
    """Erstes Argument eines Lua-Aufrufs (bis zum ersten Komma auf oberster Ebene)."""
    depth, q, out = 0, None, []
    for ch in s:
        if q:
            out.append(ch)
            if ch == q:
                q = None
            continue
        if ch in "\"'":
            q = ch
        elif ch in "({[":
            depth += 1
        elif ch in ")}]":
            if depth == 0:
                break
            depth -= 1
        elif ch == "," and depth == 0:
            break
        out.append(ch)
    return "".join(out)


def lua_bind_combos(text: str) -> list:
    """[(zeilenindex, combo)] aller einfach lesbaren hl.bind-Zeilen (Variablen wie mainMod werden aufgelöst)."""
    import re
    local = dict(re.findall(r'^\s*local\s+(\w+)\s*=\s*"([^"]*)"', text, re.M))
    out = []
    for i, ln in enumerate(text.splitlines()):
        s = ln.strip()
        if s.startswith("--"):
            continue
        m = re.match(r'(?:local\s+\w+\s*=\s*)?hl\.bind\((.*)$', s)
        if not m:
            continue
        val = ""
        for part in _split_args(m.group(1)).split(".."):
            part = part.strip()
            if len(part) >= 2 and part[0] == part[-1] and part[0] in "\"'":
                val += part[1:-1]
            elif part in local:
                val += local[part]
            else:
                val = None
                break
        if val is None:
            continue
        keys = [x.strip() for x in val.split("+") if x.strip()]
        if keys:
            out.append((i, combo(keys[:-1], keys[-1])))
    return out


def lua_conflicts(main_text: str, binds: list) -> list:
    mine = {combo(b["mods"], b["key"]) for b in binds if bind_ok(b)}
    return [i for i, c in lua_bind_combos(main_text) if c in mine]


def comment_conflicts(hdir: Path, binds: list, log) -> int:
    main = hdir / "hyprland.lua"
    if not main.is_file():
        return 0
    text = main.read_text(encoding="utf-8", errors="replace")
    idx = set(lua_conflicts(text, binds))
    if not idx:
        return 0
    bak = main.with_name(f"hyprland.lua.hyprstudio-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(main, bak)
    log(f"Sicherung: {bak}")
    lines = text.splitlines(keepends=True)
    for i in idx:
        lines[i] = "-- [Hypr Studio] " + lines[i]
        log(f"  auskommentiert: {lines[i].strip()}")
    main.write_text("".join(lines), encoding="utf-8")
    return len(idx)


def anim_list(s: dict) -> list:
    """[(leaf, speed, style)] für die aktuelle Einstellung."""
    tempo = max(0.25, float(s["anim_tempo"]))
    fast = 0.6 if s["anim_curve"] == "fast" else 1.0
    out = []
    for leaf, base, kind in ANIMS:
        speed = round(max(0.5, base * fast / tempo), 2)
        style = WIN_STYLES.get(s["win_style"]) if kind == "win" else WS_STYLES.get(s["ws_style"]) if kind == "ws" else None
        out.append((leaf, speed, style))
    return out


def _lua_str(v: str) -> str:
    return json.dumps(v, ensure_ascii=False)


def _num(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, float):
        return f"{v:.2f}".rstrip("0").rstrip(".") if v != int(v) else f"{v:.1f}"
    return str(v)


def hypr_lua(s: dict) -> str:
    if s["gradient"]:
        active = (f'{{ colors = {{{_lua_str(rgba_hypr(s["active1"]))}, {_lua_str(rgba_hypr(s["active2"]))}}}, '
                  f'angle = {int(s["angle"])} }}')
    else:
        active = _lua_str(rgba_hypr(s["active1"]))
    b = _num
    lines = [
        f"-- {MARK} – automatisch erzeugt, wird beim Anwenden überschrieben",
        "hl.config({",
        "    general = {",
        f"        gaps_in     = {s['gaps_in']},",
        f"        gaps_out    = {s['gaps_out']},",
        f"        border_size = {s['border_size']},",
        "        col = {",
        f"            active_border   = {active},",
        f"            inactive_border = {_lua_str(rgba_hypr(s['inactive']))},",
        "        },",
        f"        layout = {_lua_str(s['layout'])},",
        "    },",
        "    decoration = {",
        f"        rounding         = {s['rounding']},",
        f"        rounding_power   = {b(float(s['rounding_power']))},",
        f"        active_opacity   = {b(float(s['active_opacity']))},",
        f"        inactive_opacity = {b(float(s['inactive_opacity']))},",
        f"        dim_inactive     = {b(s['dim_inactive'])},",
        f"        dim_strength     = {b(float(s['dim_strength']))},",
        "        blur = {",
        f"            enabled  = {b(s['blur'])},",
        f"            size     = {s['blur_size']},",
        f"            passes   = {s['blur_passes']},",
        f"            vibrancy = {b(float(s['blur_vibrancy']))},",
        "        },",
        "        shadow = {",
        f"            enabled      = {b(s['shadow'])},",
        f"            range        = {s['shadow_range']},",
        f"            render_power = {s['shadow_power']},",
        f"            color        = {_lua_str(rgba_hypr(s['shadow_color']))},",
        "        },",
        "    },",
        "    animations = {",
        f"        enabled = {b(s['anim'])},",
        "    },",
        "    input = {",
        f"        kb_layout    = {_lua_str(s['kb_layout'])},",
        f"        follow_mouse = {s['follow_mouse']},",
        f"        sensitivity  = {b(float(s['sensitivity']))},",
        "        touchpad = {",
        f"            natural_scroll = {b(s['natural_scroll'])},",
        "        },",
        "    },",
        "    misc = {",
        f"        disable_hyprland_logo    = {b(s['no_logo'])},",
        f"        disable_splash_rendering = {b(s['no_logo'])},",
        "    },",
        "})",
    ]
    if s["anim"]:
        (x0, y0), (x1, y1) = CURVES[s["anim_curve"]]
        lines += ["", f'hl.curve("hs_curve", {{ type = "bezier", points = {{ {{{b(x0)}, {b(y0)}}}, {{{b(x1)}, {b(y1)}}} }} }})']
        for leaf, speed, style in anim_list(s):
            st = f", style = {_lua_str(style)}" if style else ""
            lines.append(f'hl.animation({{ leaf = "{leaf}", enabled = true, speed = {b(float(speed))}, '
                         f'bezier = "hs_curve"{st} }})')
    binds = [x for x in s["binds"] if bind_ok(x)]
    if binds:
        lines += ["", "-- Tastenkürzel"] + [bind_lua(x) for x in binds]
    return "\n".join(lines) + "\n"


def hypr_conf(s: dict) -> str:
    if s["gradient"]:
        active = f"{rgba_hypr(s['active1'])} {rgba_hypr(s['active2'])} {int(s['angle'])}deg"
    else:
        active = rgba_hypr(s["active1"])
    b = _num
    out = [
        f"# {MARK} – automatisch erzeugt, wird beim Anwenden überschrieben",
        "general {",
        f"    gaps_in = {s['gaps_in']}",
        f"    gaps_out = {s['gaps_out']}",
        f"    border_size = {s['border_size']}",
        f"    col.active_border = {active}",
        f"    col.inactive_border = {rgba_hypr(s['inactive'])}",
        f"    layout = {s['layout']}",
        "}",
        "decoration {",
        f"    rounding = {s['rounding']}",
        f"    rounding_power = {b(float(s['rounding_power']))}",
        f"    active_opacity = {b(float(s['active_opacity']))}",
        f"    inactive_opacity = {b(float(s['inactive_opacity']))}",
        f"    dim_inactive = {b(s['dim_inactive'])}",
        f"    dim_strength = {b(float(s['dim_strength']))}",
        "    blur {",
        f"        enabled = {b(s['blur'])}",
        f"        size = {s['blur_size']}",
        f"        passes = {s['blur_passes']}",
        f"        vibrancy = {b(float(s['blur_vibrancy']))}",
        "    }",
        "    shadow {",
        f"        enabled = {b(s['shadow'])}",
        f"        range = {s['shadow_range']}",
        f"        render_power = {s['shadow_power']}",
        f"        color = {rgba_hypr(s['shadow_color'])}",
        "    }",
        "}",
        "animations {",
        f"    enabled = {b(s['anim'])}",
    ]
    if s["anim"]:
        (x0, y0), (x1, y1) = CURVES[s["anim_curve"]]
        out.append(f"    bezier = hs_curve, {b(x0)}, {b(y0)}, {b(x1)}, {b(y1)}")
        for leaf, speed, style in anim_list(s):
            out.append(f"    animation = {leaf}, 1, {b(float(speed))}, hs_curve" + (f", {style}" if style else ""))
    out += [
        "}",
        "input {",
        f"    kb_layout = {s['kb_layout']}",
        f"    follow_mouse = {s['follow_mouse']}",
        f"    sensitivity = {b(float(s['sensitivity']))}",
        "    touchpad {",
        f"        natural_scroll = {b(s['natural_scroll'])}",
        "    }",
        "}",
        "misc {",
        f"    disable_hyprland_logo = {b(s['no_logo'])}",
        f"    disable_splash_rendering = {b(s['no_logo'])}",
        "}",
    ]
    binds = [x for x in s["binds"] if bind_ok(x)]
    if binds:
        out += ["", "# Tastenkürzel"] + [ln for x in binds for ln in bind_conf(x)]
    return "\n".join(out) + "\n"


def hypr_format(hdir: Path) -> str | None:
    """Lua hat ab 0.55 Vorrang (hyprland.lua wird statt hyprland.conf geladen)."""
    if (hdir / "hyprland.lua").is_file():
        return "lua"
    if (hdir / "hyprland.conf").is_file():
        return "conf"
    return None


INCLUDE = {
    "lua": ('require("hyprstudio")', "--"),
    "conf": ("source = ~/.config/hypr/hyprstudio.conf", "#"),
}


def _has_include(text: str, fmt: str) -> bool:
    c = INCLUDE[fmt][1]
    return any("hyprstudio" in ln and not ln.strip().startswith(c) for ln in text.splitlines())


def _keep_previous(target: Path) -> None:
    """Vorherige eigene Version als .bak behalten (für Rückgängig)."""
    if target.is_file():
        shutil.copy2(target, target.with_name(target.name + ".bak"))


def _backup_foreign(target: Path) -> Path | None:
    """Fremde Datei vor dem ersten Überschreiben sichern; nie etwas löschen."""
    if not target.is_file():
        return None
    if MARK in target.read_text(encoding="utf-8", errors="replace")[:300]:
        _keep_previous(target)
        return None
    dst = target.with_name(target.name + ".hyprstudio-original")
    if dst.exists():
        dst = target.with_name(f"{target.name}.hyprstudio-{time.strftime('%Y%m%d-%H%M%S')}")
    shutil.copy2(target, dst)
    return dst


def apply_hypr(s: dict, hdir: Path, log) -> tuple[bool, str]:
    if DRY and hypr_format(hdir) is None:
        hdir.mkdir(parents=True, exist_ok=True)
        (hdir / "hyprland.lua").write_text("-- Testmodus: Platzhalter für die echte hyprland.lua\n", encoding="utf-8")
    fmt = hypr_format(hdir)
    if fmt is None:
        return False, "nohypr"
    target = hdir / f"hyprstudio.{fmt}"
    _keep_previous(target)
    target.write_text(hypr_lua(s) if fmt == "lua" else hypr_conf(s), encoding="utf-8")
    log(f"→ {target}")
    main = hdir / f"hyprland.{fmt}"
    text = main.read_text(encoding="utf-8", errors="replace")
    if not _has_include(text, fmt):
        bak = main.with_name(main.name + ".hyprstudio-original")
        if not bak.exists():
            shutil.copy2(main, bak)
            log(f"Sicherung: {bak}")
        line, c = INCLUDE[fmt]
        with open(main, "a", encoding="utf-8") as fh:
            fh.write(("" if text.endswith("\n") or not text else "\n") + f"\n{c} {MARK}\n{line}\n")
        log(f"+ {main}: {line}")
    run(["hyprctl", "reload"], log)
    return True, fmt


def undo_file(target: Path) -> bool:
    bak = target.with_name(target.name + ".bak")
    if not (bak.is_file() and target.is_file()):
        return False
    cur, old = target.read_bytes(), bak.read_bytes()
    target.write_bytes(old)
    bak.write_bytes(cur)
    return True


def undo_hypr(hdir: Path, log) -> bool:
    fmt = hypr_format(hdir)
    if not fmt or not undo_file(hdir / f"hyprstudio.{fmt}"):
        return False
    run(["hyprctl", "reload"], log)
    return True


# ---------- Waybar ----------

WAYBAR_DEFAULT = {
    "position": "top", "style": "float", "height": 34, "margin": 8, "radius": 12, "spacing": 4,
    "bg": "#0e131add", "fg": "#e6edf5ff", "accent": "#3d8bfdff", "border_width": 0, "border": "#253142ff",
    "font": "JetBrainsMono Nerd Font", "font_size": 13, "icons": True, "clock24": True,
    "launcher": "rofi -show drun",
    "left": ["custom/launcher", "hyprland/workspaces"], "center": ["clock"],
    "right": ["pulseaudio", "network", "battery", "tray"],
}

MODULES = ("custom/launcher", "hyprland/workspaces", "hyprland/window", "clock", "pulseaudio", "network",
           "battery", "backlight", "bluetooth", "cpu", "memory", "temperature", "tray")

WAYBAR_PRESETS = {
    "float": {},
    "islands": {"style": "islands", "bg": "#151c26ee", "radius": 14, "height": 32},
    "classic": {"style": "bar", "margin": 0, "radius": 0, "height": 30, "bg": "#0e131aff",
                "left": ["hyprland/workspaces", "hyprland/window"], "center": ["clock"],
                "right": ["cpu", "memory", "pulseaudio", "network", "battery", "tray"]},
    "minimal": {"style": "float", "height": 28, "margin": 6, "radius": 10, "bg": "#0e131aaa",
                "left": ["hyprland/workspaces"], "center": [], "right": ["clock"]},
    "bottom": {"position": "bottom", "style": "islands", "bg": "#151c26ee",
               "left": ["custom/launcher", "hyprland/workspaces"], "center": ["hyprland/window"],
               "right": ["pulseaudio", "network", "battery", "clock", "tray"]},
    "glass": {"style": "float", "bg": "#ffffff1f", "fg": "#ffffffff", "border_width": 1, "border": "#ffffff33",
              "radius": 16, "height": 36, "margin": 10},
}

G = {  # Nerd-Font-Symbole
    "clock": "", "vol": ["", "", ""], "mute": "\U000f075f", "wifi": "",
    "eth": "\U000f0200", "nonet": "\U000f05aa", "bat": ["", "", "", "", ""],
    "cpu": "", "mem": "\U000f035b", "temp": "", "light": [""], "bt": "",
    "arch": "",
}


def waybar_state(saved: dict | None) -> dict:
    s = json.loads(json.dumps(WAYBAR_DEFAULT))
    for k, v in (saved or {}).items():
        if k in s and type(v) is type(s[k]):
            s[k] = v
    for side in ("left", "center", "right"):
        s[side] = [m for m in s[side] if m in MODULES]
    return s


def waybar_preset(name: str, base: dict | None = None) -> dict:
    s = json.loads(json.dumps(WAYBAR_DEFAULT))
    s.update(json.loads(json.dumps(WAYBAR_PRESETS.get(name, {}))))
    if base:  # Schrift und Launcher behalten
        for k in ("font", "font_size", "launcher", "kb"):
            if k in base:
                s[k] = base[k]
    return s


def module_cfg(name: str, s: dict) -> dict:
    ic = s["icons"]
    clock = "%H:%M" if s["clock24"] else "%I:%M %p"
    return {
        "custom/launcher": {"format": G["arch"] if ic else "Apps", "on-click": s["launcher"], "tooltip": False},
        "hyprland/workspaces": {"format": "{name}", "on-click": "activate", "sort-by-number": True},
        "hyprland/window": {"max-length": 48, "separate-outputs": True},
        "clock": {"format": (G["clock"] + "  " if ic else "") + "{:" + clock + "}",
                  "format-alt": "{:%A, %d.%m.%Y}", "tooltip-format": "<tt>{calendar}</tt>"},
        "pulseaudio": {"format": "{icon}  {volume}%" if ic else "Vol {volume}%",
                       "format-muted": G["mute"] if ic else "Stumm",
                       "format-icons": {"default": G["vol"]}, "on-click": "pavucontrol"},
        "network": {"format-wifi": (G["wifi"] + "  " if ic else "") + "{essid}",
                    "format-ethernet": (G["eth"] + "  " if ic else "") + "LAN",
                    "format-disconnected": G["nonet"] if ic else "Offline", "tooltip-format": "{ipaddr}"},
        "battery": {"format": "{icon}  {capacity}%" if ic else "Bat {capacity}%", "format-icons": G["bat"],
                    "states": {"warning": 30, "critical": 15}},
        "backlight": {"format": "{icon}  {percent}%" if ic else "Hell {percent}%", "format-icons": G["light"]},
        "bluetooth": {"format": G["bt"] if ic else "BT", "format-connected": (G["bt"] if ic else "BT") + " {num_connections}"},
        "cpu": {"format": (G["cpu"] + "  " if ic else "CPU ") + "{usage}%"},
        "memory": {"format": (G["mem"] + "  " if ic else "RAM ") + "{percentage}%"},
        "temperature": {"format": (G["temp"] + "  " if ic else "") + "{temperatureC}°C"},
        "tray": {"spacing": 8},
    }[name]


def waybar_json(s: dict) -> str:
    cfg = {"layer": "top", "position": s["position"], "height": s["height"], "spacing": s["spacing"]}
    if s["style"] != "bar" and s["margin"]:
        m = s["margin"]
        cfg.update({"margin-top": m if s["position"] == "top" else 0,
                    "margin-bottom": m if s["position"] == "bottom" else 0,
                    "margin-left": m * 2, "margin-right": m * 2})
    cfg["modules-left"] = s["left"]
    cfg["modules-center"] = s["center"]
    cfg["modules-right"] = s["right"]
    for m in s["left"] + s["center"] + s["right"]:
        cfg[m] = module_cfg(m, s)
    return f"// {MARK} – automatisch erzeugt, wird beim Anwenden überschrieben\n" + \
        json.dumps(cfg, indent=4, ensure_ascii=False) + "\n"


CSS_IDS = {"custom/launcher": "#custom-launcher", "hyprland/workspaces": "#workspaces",
           "hyprland/window": "#window", "clock": "#clock", "pulseaudio": "#pulseaudio", "network": "#network",
           "battery": "#battery", "backlight": "#backlight", "bluetooth": "#bluetooth", "cpu": "#cpu",
           "memory": "#memory", "temperature": "#temperature", "tray": "#tray"}


def waybar_css(s: dict) -> str:
    r = s["radius"]
    fg, acc, bg = s["fg"], s["accent"], s["bg"]
    border = f"{s['border_width']}px solid {rgba_css(s['border'])}" if s["border_width"] else "none"
    ids = ", ".join(CSS_IDS[m] for m in MODULES)
    if s["style"] == "islands":
        win = "background: transparent;"
        mod = (f"background: {rgba_css(bg)}; border-radius: {r}px; border: {border}; padding: 0 12px;"
               " margin: 0 3px;")
    else:
        win = f"background: {rgba_css(bg)}; border-radius: {r if s['style'] == 'float' else 0}px; border: {border};"
        mod = "padding: 0 10px;"
    return f"""/* {MARK} – automatisch erzeugt, wird beim Anwenden überschrieben */
* {{
    font-family: "{s['font']}", "Symbols Nerd Font", sans-serif;
    font-size: {s['font_size']}px;
    min-height: 0;
}}

window#waybar {{
    {win}
    color: {rgba_css(fg)};
}}

{ids} {{
    {mod}
    color: {rgba_css(fg)};
}}

#custom-launcher {{
    color: {rgba_css(acc)};
    font-size: {s['font_size'] + 3}px;
}}

#workspaces button {{
    padding: 0 7px;
    color: {rgba_css(fg, 0.55)};
    background: transparent;
    border: none;
    border-radius: {max(4, r // 2)}px;
    box-shadow: none;
}}

#workspaces button:hover {{
    background: {rgba_css(fg, 0.08)};
}}

#workspaces button.active {{
    color: {rgba_css(acc)};
    background: {rgba_css(acc, 0.18)};
}}

#battery.warning {{ color: #d29922; }}
#battery.critical {{ color: #e5534b; }}

tooltip {{
    background: {rgba_css(bg, 0.95)};
    border: 1px solid {rgba_css(fg, 0.15)};
    border-radius: {max(6, r // 2)}px;
}}
"""


def waybar_files(wdir: Path) -> tuple[Path, Path]:
    for n in ("config.jsonc", "config.json", "config"):
        if (wdir / n).is_file():
            return wdir / n, wdir / "style.css"
    return wdir / "config.jsonc", wdir / "style.css"


def apply_waybar(s: dict, wdir: Path, log) -> tuple[bool, str]:
    wdir.mkdir(parents=True, exist_ok=True)
    cfg, css = waybar_files(wdir)
    for target, data in ((cfg, waybar_json(s)), (css, waybar_css(s))):
        bak = _backup_foreign(target)
        if bak:
            log(f"Sicherung: {bak}")
        target.write_text(data, encoding="utf-8")
        log(f"→ {target}")
    restart_waybar(log)
    return True, ""


def undo_waybar(wdir: Path, log) -> bool:
    cfg, css = waybar_files(wdir)
    done = [undo_file(f) for f in (cfg, css)]
    if any(done):
        restart_waybar(log)
    return any(done)


def restart_waybar(log) -> None:
    # SIGUSR2 lädt neu, stürzt aber bei manchen Versionen ab – Neustart ist zuverlässiger
    run(["pkill", "-x", "waybar"], log, quiet=True)
    if DRY:
        log("$ waybar &  (Testmodus)")
        return
    time.sleep(0.3)
    try:
        subprocess.Popen(["waybar"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, start_new_session=True)
        log("$ waybar &")
    except OSError as e:
        log(f"waybar: {e}")


# ---------- Prozesse ----------

def run(cmd: list, log, quiet: bool = False) -> bool:
    if DRY:
        log("$ " + " ".join(cmd) + "  (Testmodus)")
        return True
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.TimeoutExpired) as e:
        log(f"$ {' '.join(cmd)}: {e}")
        return False
    if not quiet or p.returncode == 0:
        log("$ " + " ".join(cmd))
        for ln in (p.stdout + p.stderr).strip().splitlines():
            log("  " + ln)
    return p.returncode == 0


def which(name: str) -> bool:
    return DRY or shutil.which(name) is not None
