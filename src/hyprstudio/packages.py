"""Optionale Programme selbst auswählen und installieren (nichts davon wird automatisch installiert). Ohne Qt."""

import shutil
import subprocess

from . import model

# key: (Gruppe, Prüf-Befehl oder Font-Name, {Paketmanager: [Pakete]})
PACKAGES = {
    "rofi": ("launcher", "rofi", {"pacman": ["rofi"], "apt": ["rofi"], "dnf": ["rofi-wayland"], "zypper": ["rofi"]}),
    "wofi": ("launcher", "wofi", {"pacman": ["wofi"], "apt": ["wofi"], "dnf": ["wofi"], "zypper": ["wofi"]}),
    "fuzzel": ("launcher", "fuzzel", {"pacman": ["fuzzel"], "apt": ["fuzzel"], "dnf": ["fuzzel"], "zypper": ["fuzzel"]}),
    "waybar": ("bar", "waybar", {"pacman": ["waybar"], "apt": ["waybar"], "dnf": ["waybar"], "zypper": ["waybar"]}),
    "nerdfont": ("bar", "font:JetBrainsMono Nerd Font", {"pacman": ["ttf-jetbrains-mono-nerd", "ttf-nerd-fonts-symbols-mono"]}),
    "kitty": ("tools", "kitty", {"pacman": ["kitty"], "apt": ["kitty"], "dnf": ["kitty"], "zypper": ["kitty"]}),
    "pavucontrol": ("bar", "pavucontrol", {"pacman": ["pavucontrol"], "apt": ["pavucontrol"], "dnf": ["pavucontrol"],
                                           "zypper": ["pavucontrol"]}),
    "screenshot": ("tools", "grim", {"pacman": ["grim", "slurp", "wl-clipboard"], "apt": ["grim", "slurp", "wl-clipboard"],
                                     "dnf": ["grim", "slurp", "wl-clipboard"], "zypper": ["grim", "slurp", "wl-clipboard"]}),
    "media": ("tools", "playerctl", {"pacman": ["playerctl", "brightnessctl"], "apt": ["playerctl", "brightnessctl"],
                                     "dnf": ["playerctl", "brightnessctl"], "zypper": ["playerctl", "brightnessctl"]}),
    "hyprpicker": ("tools", "hyprpicker", {"pacman": ["hyprpicker"], "dnf": ["hyprpicker"]}),
    "hyprlock": ("tools", "hyprlock", {"pacman": ["hyprlock"], "dnf": ["hyprlock"]}),
    "hyprcursor": ("tools", "hyprcursor-util", {"pacman": ["hyprcursor"], "dnf": ["hyprcursor"]}),
    "hyprpaper": ("tools", "hyprpaper", {"pacman": ["hyprpaper"], "dnf": ["hyprpaper"]}),
    "cliphist": ("tools", "cliphist", {"pacman": ["cliphist"]}),
}
GROUPS = ("launcher", "bar", "tools")
DRY_INSTALLED: set = set()


def manager() -> str | None:
    if model.DRY:
        return "pacman"
    for pm, exe in (("pacman", "pacman"), ("apt", "apt-get"), ("dnf", "dnf"), ("zypper", "zypper")):
        if shutil.which(exe):
            return pm
    return None


def installed(key: str) -> bool:
    check = PACKAGES[key][1]
    if model.DRY:  # Testmodus: etwas gemischt anzeigen, „Installiertes“ merken
        return key in ("waybar", "rofi") or key in DRY_INSTALLED
    if check.startswith("font:"):
        try:
            out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=8).stdout
        except (OSError, subprocess.TimeoutExpired):
            return False
        return check[5:].lower() in out.lower()
    return shutil.which(check) is not None


def available(key: str, pm: str | None) -> bool:
    return bool(pm and PACKAGES[key][2].get(pm))


def command(keys: list, pm: str) -> list:
    """Befehl für pkexec (läuft als root, ohne Rückfrage im Terminal)."""
    pkgs = []
    for k in keys:
        pkgs += [p for p in PACKAGES[k][2].get(pm, []) if p not in pkgs]
    if not pkgs:
        return []
    return {
        "pacman": ["pacman", "-S", "--needed", "--noconfirm", *pkgs],
        "apt": ["apt-get", "install", "-y", *pkgs],
        "dnf": ["dnf", "install", "-y", *pkgs],
        "zypper": ["zypper", "-n", "in", *pkgs],
    }[pm]
