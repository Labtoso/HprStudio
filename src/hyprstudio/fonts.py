"""Schriftarten mit einem Klick installieren: Nerd Fonts von GitHub nach ~/.local/share/fonts (ohne root). Ohne Qt."""

import io
import subprocess
import tarfile
import urllib.request
from pathlib import Path

import hyprstudio
from . import model

URL = "https://github.com/ryanoasis/nerd-fonts/releases/latest/download/{}.tar.xz"
FONT_EXT = (".ttf", ".otf")

# (Archivname bei nerd-fonts, Schriftfamilie nach der Installation)
CATALOG = [
    ("JetBrainsMono", "JetBrainsMono Nerd Font"), ("FiraCode", "FiraCode Nerd Font"),
    ("Hack", "Hack Nerd Font"), ("CascadiaCode", "CaskaydiaCove Nerd Font"),
    ("CascadiaMono", "CaskaydiaMono Nerd Font"), ("Meslo", "MesloLGS Nerd Font"),
    ("Iosevka", "Iosevka Nerd Font"), ("IosevkaTerm", "IosevkaTerm Nerd Font"),
    ("SourceCodePro", "SauceCodePro Nerd Font"), ("RobotoMono", "RobotoMono Nerd Font"),
    ("UbuntuMono", "UbuntuMono Nerd Font"), ("Ubuntu", "Ubuntu Nerd Font"), ("UbuntuSans", "UbuntuSans Nerd Font"),
    ("Noto", "NotoSans Nerd Font"), ("DejaVuSansMono", "DejaVuSansM Nerd Font"),
    ("FiraMono", "FiraMono Nerd Font"), ("GeistMono", "GeistMono Nerd Font"),
    ("IBMPlexMono", "BlexMono Nerd Font"), ("Inconsolata", "Inconsolata Nerd Font"),
    ("VictorMono", "VictorMono Nerd Font"), ("Mononoki", "Mononoki Nerd Font"),
    ("SpaceMono", "SpaceMono Nerd Font"), ("ZedMono", "ZedMono Nerd Font"), ("Lilex", "Lilex Nerd Font"),
    ("Monaspace", "MonaspiceNe Nerd Font"), ("0xProto", "0xProto Nerd Font"), ("Agave", "Agave Nerd Font"),
    ("ComicShannsMono", "ComicShannsMono Nerd Font"), ("FantasqueSansMono", "FantasqueSansM Nerd Font"),
    ("Hasklig", "Hasklug Nerd Font"), ("IntelOneMono", "IntoneMono Nerd Font"), ("Terminus", "Terminess Nerd Font"),
    ("CodeNewRoman", "CodeNewRoman Nerd Font"), ("Go-Mono", "GoMono Nerd Font"), ("Arimo", "Arimo Nerd Font"),
    ("Tinos", "Tinos Nerd Font"), ("NerdFontsSymbolsOnly", "Symbols Nerd Font"),
]


def fonts_dir() -> Path:
    if model.DRY:
        return model.CACHE / "testmodus" / "fonts"
    return Path.home() / ".local/share/fonts/HyprStudio"


def family_of(archive: str) -> str:
    return next((f for a, f in CATALOG if a == archive), archive + " Nerd Font")


def extract(data: bytes, dest: Path) -> list:
    """Nur Schriftdateien flach in dest ablegen (keine Pfade aus dem Archiv übernehmen)."""
    dest.mkdir(parents=True, exist_ok=True)
    out = []
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:*") as tar:
        for m in tar.getmembers():
            name = Path(m.name).name
            if not m.isfile() or not name.lower().endswith(FONT_EXT) or name.startswith("."):
                continue
            target = dest / name
            if not target.exists():
                target.write_bytes(tar.extractfile(m).read())
            out.append(target)
    return out


def install(archive: str, log) -> list:
    """Archiv laden, entpacken, Font-Cache erneuern. Gibt die Schriftdateien zurück."""
    url = URL.format(archive)
    log(f"↓ {url}")
    req = urllib.request.Request(url, headers={"User-Agent": f"HyprStudio/{hyprstudio.__version__}"})
    with urllib.request.urlopen(req, timeout=180) as r:
        data = r.read()
    files = extract(data, fonts_dir() / archive)
    log(f"→ {fonts_dir() / archive} ({len(files)})")
    if not model.DRY:
        try:
            subprocess.run(["fc-cache", "-f", str(fonts_dir())], capture_output=True, timeout=120)
        except (OSError, subprocess.TimeoutExpired) as e:
            log(f"fc-cache: {e}")
    return files


def local_files() -> list:
    """Bereits über Hypr Studio installierte Schriftdateien (für Qt nachladen)."""
    d = fonts_dir()
    return [f for f in d.rglob("*") if f.suffix.lower() in FONT_EXT] if d.is_dir() else []
