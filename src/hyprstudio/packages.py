"""Optionale Programme selbst auswählen und installieren (nichts davon wird automatisch installiert). Ohne Qt."""

import glob
import shutil
import subprocess

from . import appearance, model

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
    "qtdark": ("tools", "file:" + "|".join(appearance.KDE_PLUGIN_GLOBS),
               {"pacman": ["plasma-integration"], "apt": ["plasma-integration"], "dnf": ["plasma-integration"],
                "zypper": ["plasma6-integration-plugin"]}),
    "fastfetch": ("tools", "fastfetch", {"pacman": ["fastfetch"], "apt": ["fastfetch"], "dnf": ["fastfetch"],
                                         "zypper": ["fastfetch"]}),
}
GROUPS = ("launcher", "bar", "tools")
DRY_INSTALLED: set = set()
DRY_REMOVED: set = set()


def manager() -> str | None:
    if model.DRY:
        return "pacman"
    for pm, exe in (("pacman", "pacman"), ("apt", "apt-get"), ("dnf", "dnf"), ("zypper", "zypper")):
        if shutil.which(exe):
            return pm
    return None


def installed(key: str) -> bool:
    if key not in PACKAGES:  # z. B. L Launcher: gehört zu Hypr Studio
        return True
    check = PACKAGES[key][1]
    if model.DRY:  # Testmodus: etwas gemischt anzeigen, „Installiertes“ merken
        return (key in ("waybar", "rofi") or key in DRY_INSTALLED) and key not in DRY_REMOVED
    if check.startswith("file:"):  # z. B. Qt-Plugin ohne eigenen Befehl
        return any(glob.glob(g) for g in check[5:].split("|"))
    if check.startswith("font:"):
        try:
            out = subprocess.run(["fc-list"], capture_output=True, text=True, timeout=8).stdout
        except (OSError, subprocess.TimeoutExpired):
            return False
        return check[5:].lower() in out.lower()
    return shutil.which(check) is not None


POLKIT_AGENTS = ("hyprpolkitagent", "polkit-kde-authentication-agent-1", "polkit-gnome-authentication-agent-1",
                 "polkit-mate-authentication-agent-1", "lxpolkit", "lxqt-policykit-agent", "xfce-polkit",
                 "polkit-agent-helper", "soteria")


def polkit_agent() -> bool:
    """Läuft ein Polkit-Agent (Passwortfenster für pkexec)? Unter Hyprland fehlt er oft → dann Terminal + sudo."""
    if model.DRY:
        return True
    try:
        out = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True, timeout=5).stdout
    except (OSError, subprocess.TimeoutExpired):
        return False
    return any(a in out for a in POLKIT_AGENTS)


def fail_reason(output: str) -> str | None:
    """Häufige Paketmanager-Fehler → i18n-Schlüssel mit verständlichem Hinweis."""
    o = output.lower()
    if "failed retrieving file" in o or "404" in o or "could not resolve" in o or "failed to synchronize" in o:
        return "pkg.err_sync"
    if "target not found" in o or "unable to locate package" in o or "no match for argument" in o:
        return "pkg.err_notfound"
    if "unable to lock database" in o or "could not get lock" in o:
        return "pkg.err_lock"
    if "not authorized" in o or "authentication" in o or "no authentication agent" in o:
        return "pkg.err_auth"
    return None


def available(key: str, pm: str | None) -> bool:
    return bool(pm and key in PACKAGES and PACKAGES[key][2].get(pm))


def pkg_names(keys: list, pm: str) -> list:
    pkgs = []
    for k in keys:
        pkgs += [p for p in PACKAGES[k][2].get(pm, []) if p not in pkgs]
    return pkgs


def _present(pkgs: list, pm: str) -> list:
    """Nur Pakete, die wirklich installiert sind (sonst bricht das Entfernen ab)."""
    if model.DRY:
        return pkgs
    q = {"pacman": ["pacman", "-Q"], "apt": ["dpkg", "-s"], "dnf": ["rpm", "-q"], "zypper": ["rpm", "-q"]}[pm]
    out = []
    for p in pkgs:
        try:
            if subprocess.run(q + [p], capture_output=True, timeout=8).returncode == 0:
                out.append(p)
        except (OSError, subprocess.TimeoutExpired):
            out.append(p)
    return out


def remove_command(keys: list, pm: str) -> list:
    """Entfernen per pkexec; pacman -Rs nimmt nicht mehr gebrauchte Abhängigkeiten mit."""
    pkgs = _present(pkg_names(keys, pm), pm)
    if not pkgs:
        return []
    return {
        "pacman": ["pacman", "-Rs", "--noconfirm", *pkgs],
        "apt": ["apt-get", "remove", "-y", *pkgs],
        "dnf": ["dnf", "remove", "-y", *pkgs],
        "zypper": ["zypper", "-n", "rm", *pkgs],
    }[pm]


def command(keys: list, pm: str) -> list:
    """Befehl für pkexec (läuft als root, ohne Rückfrage im Terminal)."""
    pkgs = pkg_names(keys, pm)
    if not pkgs:
        return []
    return {
        "pacman": ["pacman", "-S", "--needed", "--noconfirm", *pkgs],
        "apt": ["apt-get", "install", "-y", *pkgs],
        "dnf": ["dnf", "install", "-y", *pkgs],
        "zypper": ["zypper", "-n", "in", *pkgs],
    }[pm]
