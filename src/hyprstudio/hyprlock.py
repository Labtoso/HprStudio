"""Hyprlock (Sperrbildschirm): Zustand, Presets und ~/.config/hypr/hyprlock.conf. Ohne Qt.

hyprlock.conf (hyprlang, Wiki):
    general { hide_cursor, grace, ignore_empty_input }
    background { monitor =, path = screenshot | Bild, color, blur_passes, blur_size, brightness, contrast, vibrancy }
    image { path, size, rounding (-1 = Kreis), border_size, border_color, position, halign, valign }
    label { text = $TIME | cmd[update:1000] …, color, font_size, font_family, position, halign, valign }
    input-field { size = B, H; outline_thickness; outer_color; inner_color; font_color; check_color; fail_color;
                  rounding; placeholder_text; fade_on_empty; dots_center; position; halign; valign }
Position: Mitte = 0, 0; positives y geht nach oben.
"""

import json
import os
from pathlib import Path

from . import model
from .model import MARK, rgba_hypr

BGS = ("screenshot", "wallpaper", "image", "color")
CLOCKS = ("24", "12", "sec")
DATES = ("long", "short", "iso")
DATE_FMT = {"long": "%A, %d %B", "short": "%d.%m.%Y", "iso": "%Y-%m-%d"}

LOCK_DEFAULT = {
    "bg": "screenshot", "bg_path": "", "bg_color": "#1e1e2eff",
    "blur_passes": 3, "blur_size": 7, "brightness": 0.8, "contrast": 0.9, "vibrancy": 0.17,
    "clock": True, "clock_fmt": "24", "clock_size": 90, "date": True, "date_fmt": "long", "date_size": 20,
    "greet": True, "greet_text": "Hi, $USER",
    "avatar": False, "avatar_path": "~/.face.icon", "avatar_size": 110,
    "font": "JetBrainsMono Nerd Font", "text_color": "#cdd6f4ff",
    "accent": "#89b4faff", "inner_color": "#1e1e2ecc", "input_text": "#cdd6f4ff",
    "check_color": "#f9e2afff", "fail_color": "#f38ba8ff",
    "input_w": 300, "input_h": 52, "rounding": -1, "outline": 3, "input_y": -120,
    "placeholder": "Password …", "fade_empty": False, "dots_center": True,
    "hide_cursor": True, "grace": 0, "ignore_empty": True, "lock_bind": False,
}

PRESETS = {
    "catppuccin": {},
    "glass": {"bg": "wallpaper", "blur_passes": 4, "blur_size": 9, "brightness": 0.75, "accent": "#ffffff66",
              "inner_color": "#ffffff1a", "text_color": "#ffffffff", "input_text": "#ffffffff", "outline": 2},
    "tokyo": {"bg": "screenshot", "accent": "#7aa2f7ff", "inner_color": "#1a1b26dd", "text_color": "#c0caf5ff",
              "input_text": "#c0caf5ff", "fail_color": "#f7768eff", "check_color": "#e0af68ff", "rounding": 12},
    "nord": {"bg": "color", "bg_color": "#2e3440ff", "accent": "#88c0d0ff", "inner_color": "#3b4252ff",
             "text_color": "#eceff4ff", "input_text": "#eceff4ff", "fail_color": "#bf616aff", "check_color": "#ebcb8bff",
             "rounding": 8, "greet": False},
    "minimal": {"bg": "color", "bg_color": "#000000ff", "clock_size": 64, "date": False, "greet": False,
                "accent": "#ffffff33", "inner_color": "#00000000", "text_color": "#ffffffff",
                "input_text": "#ffffffff", "outline": 1, "rounding": 0, "input_w": 260, "input_h": 44,
                "fade_empty": True},
    "bigclock": {"bg": "wallpaper", "clock_size": 150, "clock_fmt": "24", "date_size": 26, "brightness": 0.6,
                 "blur_passes": 2, "greet": False, "accent": "#33ccffee", "inner_color": "#11111bcc",
                 "text_color": "#ffffffff", "input_text": "#ffffffff", "input_y": -220},
    "gruvbox": {"bg": "screenshot", "accent": "#d79921ff", "inner_color": "#282828ee", "text_color": "#ebdbb2ff",
                "input_text": "#ebdbb2ff", "fail_color": "#cc241dff", "check_color": "#98971aff", "rounding": 6,
                "avatar": True},
    "rose": {"bg": "wallpaper", "accent": "#ebbcbaff", "inner_color": "#191724dd", "text_color": "#e0def4ff",
             "input_text": "#e0def4ff", "fail_color": "#eb6f92ff", "check_color": "#f6c177ff", "avatar": True},
}
LOOK_KEYS = tuple(k for k in LOCK_DEFAULT if k not in ("lock_bind", "hide_cursor", "grace", "ignore_empty",
                                                         "greet_text", "avatar_path", "bg_path", "placeholder"))


def lock_state(saved: dict | None) -> dict:
    s = json.loads(json.dumps(LOCK_DEFAULT))
    for k, v in (saved or {}).items():
        if k not in s:
            continue
        if type(v) is type(s[k]):
            s[k] = v
        elif isinstance(s[k], float) and type(v) is int:
            s[k] = float(v)
    for k, opts in (("bg", BGS), ("clock_fmt", CLOCKS), ("date_fmt", DATES)):
        if s[k] not in opts:
            s[k] = LOCK_DEFAULT[k]
    return s


def preset_state(name: str, base: dict | None = None) -> dict:
    s = lock_state(base)
    for k in LOOK_KEYS:
        s[k] = LOCK_DEFAULT[k]
    s.update(PRESETS.get(name, {}))
    return s


def bg_path(s: dict, wallpaper: str = "") -> str:
    """Bild für background { path }: screenshot, das Hyprpaper-Bild oder ein eigenes Bild; leer = nur Farbe."""
    if s["bg"] == "screenshot":
        return "screenshot"
    if s["bg"] == "wallpaper":
        return first_image(wallpaper)
    if s["bg"] == "image":
        return s["bg_path"]
    return ""


def first_image(path: str) -> str:
    """Hyprlock kann keinen Ordner: bei einer Diashow das erste Bild nehmen."""
    if not path:
        return ""
    p = Path(os.path.expanduser(path))
    if p.is_dir():
        from .paper import IMAGE_EXT
        imgs = sorted(f for f in p.iterdir() if f.suffix.lower() in IMAGE_EXT)
        return str(imgs[0]) if imgs else ""
    return path


def _q(text: str) -> str:
    return text.replace("\n", " ").strip()


def _label(text: str, color: str, size: int, font: str, y: int) -> list:
    return ["label {", "    monitor =", f"    text = {text}", f"    color = {rgba_hypr(color)}",
            f"    font_size = {size}", f"    font_family = {font}", f"    position = 0, {y}",
            "    halign = center", "    valign = center", "}", ""]


def layout(s: dict) -> dict:
    """y-Positionen (Mitte = 0, oben positiv) – gleich für Datei und Vorschau."""
    y = {"input": s["input_y"]}
    top = s["input_y"] + s["input_h"] // 2 + 30
    if s["greet"]:
        y["greet"] = top + 14
        top += 50
    if s["avatar"]:
        y["avatar"] = top + s["avatar_size"] // 2
        top += s["avatar_size"] + 30
    if s["date"]:
        y["date"] = top + s["date_size"]
        top += s["date_size"] * 2 + 10
    if s["clock"]:
        y["clock"] = top + int(s["clock_size"] * 0.6)
    return y


def clock_text(s: dict) -> str:
    if s["clock_fmt"] == "12":
        return "$TIME12"
    if s["clock_fmt"] == "sec":
        return 'cmd[update:1000] date +"%H:%M:%S"'
    return "$TIME"


def lock_conf(s: dict, wallpaper: str = "") -> str:
    font = _q(s["font"]) or "Sans"
    y = layout(s)
    out = [f"# {MARK} – automatisch erzeugt, wird beim Anwenden überschrieben", "",
           "general {", f"    hide_cursor = {str(s['hide_cursor']).lower()}", f"    grace = {s['grace']}",
           f"    ignore_empty_input = {str(s['ignore_empty']).lower()}", "}", "",
           "background {", "    monitor ="]
    path = bg_path(s, wallpaper)
    if path:
        out.append(f"    path = {path}")
    out += [f"    color = {rgba_hypr(s['bg_color'])}", f"    blur_passes = {s['blur_passes']}",
            f"    blur_size = {s['blur_size']}", f"    brightness = {s['brightness']:.2f}",
            f"    contrast = {s['contrast']:.2f}", f"    vibrancy = {s['vibrancy']:.2f}", "}", ""]
    if s["avatar"] and s["avatar_path"]:
        out += ["image {", "    monitor =", f"    path = {s['avatar_path']}", f"    size = {s['avatar_size']}",
                "    rounding = -1", f"    border_size = {s['outline']}", f"    border_color = {rgba_hypr(s['accent'])}",
                f"    position = 0, {y['avatar']}", "    halign = center", "    valign = center", "}", ""]
    if s["clock"]:
        out += _label(clock_text(s), s["text_color"], s["clock_size"], font, y["clock"])
    if s["date"]:
        out += _label(f'cmd[update:60000] date +"{DATE_FMT[s["date_fmt"]]}"', s["text_color"], s["date_size"], font,
                      y["date"])
    if s["greet"] and _q(s["greet_text"]):
        out += _label(_q(s["greet_text"]), s["text_color"], 16, font, y["greet"])
    out += ["input-field {", "    monitor =", f"    size = {s['input_w']}, {s['input_h']}",
            f"    outline_thickness = {s['outline']}", f"    outer_color = {rgba_hypr(s['accent'])}",
            f"    inner_color = {rgba_hypr(s['inner_color'])}", f"    font_color = {rgba_hypr(s['input_text'])}",
            f"    font_family = {font}", f"    check_color = {rgba_hypr(s['check_color'])}",
            f"    fail_color = {rgba_hypr(s['fail_color'])}", f"    rounding = {s['rounding']}",
            f"    placeholder_text = {_q(s['placeholder'])}", "    fail_text = $FAIL ($ATTEMPTS)",
            f"    fade_on_empty = {str(s['fade_empty']).lower()}", f"    dots_center = {str(s['dots_center']).lower()}",
            "    dots_size = 0.25", "    dots_spacing = 0.3",
            f"    position = 0, {y['input']}", "    halign = center", "    valign = center", "}"]
    return "\n".join(out) + "\n"


def lock_file(hdir: Path) -> Path:
    return hdir / "hyprlock.conf"


def apply_lock(s: dict, hdir: Path, log, wallpaper: str = "") -> tuple[bool, str]:
    if s["bg"] == "image" and not s["bg_path"]:
        return False, "lock.nopath"
    hdir.mkdir(parents=True, exist_ok=True)
    f = lock_file(hdir)
    bak = model._backup_foreign(f)
    if bak:
        log(f"Sicherung: {bak}")
    f.write_text(lock_conf(s, wallpaper), encoding="utf-8")
    log(f"→ {f}")
    return True, ""


LOCK_BIND = {"mods": ["SUPER"], "key": "L", "action": "exec", "arg": "hyprlock", "flags": []}


def has_lock_bind(binds: list) -> bool:
    return any(b.get("action") == "exec" and b.get("arg", "").strip() == "hyprlock" for b in binds)


def set_lock_bind(binds: list, on: bool) -> list:
    rest = [b for b in binds if not (b.get("action") == "exec" and b.get("arg", "").strip() == "hyprlock")]
    return rest + [dict(LOCK_BIND)] if on else rest
