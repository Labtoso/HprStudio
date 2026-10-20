"""Hell/Dunkel für alle Programme: GTK (settings.ini + gsettings) und KDE/Qt (plasma-apply-colorscheme). Ohne Qt."""

import shutil
from pathlib import Path

from . import model
from .model import MARK

MODES = ("dark", "light")
DEFAULT = "dark"


def set_ini(f: Path, key: str, value: str, log) -> None:
    """Schlüssel in [Settings] setzen, Rest der Datei behalten; fremde Datei vorher sichern."""
    f.parent.mkdir(parents=True, exist_ok=True)
    bak = model._backup_foreign(f)
    if bak:
        log(f"Sicherung: {bak}")
    lines = f.read_text(encoding="utf-8", errors="replace").splitlines() if f.is_file() else []
    if not any(MARK in ln for ln in lines[:3]):
        lines.insert(0, f"# {MARK}")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == "[Settings]"), None)
    if start is None:
        lines += ["[Settings]", f"{key}={value}"]
    else:
        end = next((i for i in range(start + 1, len(lines)) if lines[i].strip().startswith("[")), len(lines))
        hit = next((i for i in range(start + 1, end) if lines[i].split("=", 1)[0].strip() == key), None)
        if hit is None:
            lines.insert(start + 1, f"{key}={value}")
        else:
            lines[hit] = f"{key}={value}"
    with open(f, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(lines) + "\n")
    log(f"→ {f}: {key}={value}")


def apply(mode: str, cfg_home: Path, log) -> bool:
    dark = mode == "dark"
    for d in ("gtk-3.0", "gtk-4.0"):
        set_ini(cfg_home / d / "settings.ini", "gtk-application-prefer-dark-theme", "1" if dark else "0", log)
    if model.which("gsettings"):
        model.run(["gsettings", "set", "org.gnome.desktop.interface", "color-scheme",
                   "prefer-dark" if dark else "prefer-light"], log, quiet=True)
        model.run(["gsettings", "set", "org.gnome.desktop.interface", "gtk-theme",
                   "Adwaita-dark" if dark else "Adwaita"], log, quiet=True)
    if model.DRY or shutil.which("plasma-apply-colorscheme"):
        model.run(["plasma-apply-colorscheme", "BreezeDark" if dark else "BreezeLight"], log, quiet=True)
    return True
