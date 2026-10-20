"""Baut alles: Icons, portable .pyz, Quell-Tarball fürs Arch-Paket und den installer/-Ordner.
Jede Version landet zusätzlich komplett (Install, Uninstall, Portable) in installer/_old/<Version>/;
in installer/arch/ bleibt nur die aktuelle – ältere Tarballs werden dorthin verschoben (nie gelöscht).

Start:  python build.py      (läuft unter Windows und Linux, braucht PySide6 nur für die Icons)
"""

import io
import os
import shutil
import sys
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
import hyprstudio  # noqa: E402

VER = hyprstudio.__version__
NAME = f"labtoso-hyprstudio-{VER}"
INST = ROOT / "installer"
OLD = INST / "_old"
DIST = ROOT / "dist"
SIZES = (16, 32, 48, 64, 128, 256)
EXEC = ("hypr-studio", "l-launcher", "install.sh", "uninstall.sh")


def lf(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n")


def render_icons() -> None:
    from PySide6 import QtCore, QtGui, QtSvg, QtWidgets  # noqa: F401
    _ = QtWidgets.QApplication.instance() or QtWidgets.QApplication(["build"])
    r = QtSvg.QSvgRenderer(str(SRC / "hyprstudio/assets/hyprstudio.svg"))
    out = ROOT / "packaging/icons"
    out.mkdir(parents=True, exist_ok=True)
    for s in SIZES:
        img = QtGui.QImage(s, s, QtGui.QImage.Format.Format_ARGB32)
        img.fill(0)
        p = QtGui.QPainter(img)
        p.setRenderHint(QtGui.QPainter.RenderHint.Antialiasing)
        r.render(p, QtCore.QRectF(0, 0, s, s))
        p.end()
        img.save(str(out / f"{s}.png"))
    print("Icons:", ", ".join(map(str, SIZES)))


def src_files():
    for f in sorted((SRC / "hyprstudio").rglob("*")):
        if f.is_file() and "__pycache__" not in f.parts:
            yield f


def build_pyz() -> Path:
    DIST.mkdir(exist_ok=True)
    target = DIST / "Hypr-Studio.pyz"
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for f in src_files():
            data = f.read_bytes()
            if f.suffix == ".py":
                data = lf(data)
            z.writestr(str(f.relative_to(SRC)).replace("\\", "/"), data)
        z.writestr("__main__.py", "import sys\nfrom hyprstudio.__main__ import main\nsys.exit(main())\n")
    with open(target, "wb") as fh:
        fh.write(b"#!/usr/bin/env python3\n")
        fh.write(buf.getvalue())
    print("Portable:", target.name, f"{target.stat().st_size // 1024} KB")
    return target


def build_tarball() -> Path:
    DIST.mkdir(exist_ok=True)
    target = DIST / f"{NAME}.tar.gz"
    files = list(src_files()) + [f for f in sorted((ROOT / "packaging").rglob("*")) if f.is_file()]
    with tarfile.open(target, "w:gz") as tar:
        for f in files:
            rel = f.relative_to(ROOT).as_posix()
            data = f.read_bytes()
            if f.suffix in (".py", ".sh", ".desktop", ".svg", "") or f.name == "PKGBUILD":
                data = lf(data)
            ti = tarfile.TarInfo(f"{NAME}/{rel}")
            ti.size = len(data)
            ti.mode = 0o755 if f.name in EXEC else 0o644
            ti.mtime = int(f.stat().st_mtime)
            tar.addfile(ti, io.BytesIO(data))
    print("Quellen:", target.name)
    return target


def write_lf(path: Path, text: str) -> None:
    path.write_bytes(lf(text.encode("utf-8")))


def build_installer(pyz: Path, tarball: Path) -> None:
    (INST / "portable").mkdir(parents=True, exist_ok=True)
    (INST / "arch").mkdir(parents=True, exist_ok=True)
    shutil.copy2(pyz, INST / "portable" / pyz.name)
    shutil.copy2(tarball, INST / "arch" / tarball.name)
    write_lf(INST / "arch/PKGBUILD", (ROOT / "packaging/PKGBUILD").read_text(encoding="utf-8"))
    write_lf(INST / "arch/install.sh", (ROOT / "packaging/install.sh").read_text(encoding="utf-8"))
    write_lf(INST / "uninstall.sh", (ROOT / "packaging/uninstall.sh").read_text(encoding="utf-8"))
    write_lf(INST / "Install.sh", INSTALL_SH)
    write_lf(INST / "Portable.sh", PORTABLE_SH)
    write_lf(INST / "Hypr Studio.desktop", PORTABLE_DESKTOP)
    print("installer/ aktualisiert")
    archive_versions()


def _pyz_from_tar(tar: tarfile.TarFile, prefix: str) -> bytes:
    """Portable .pyz aus dem Quellcode im Tarball einer Version."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for m in tar.getmembers():
            if m.isfile() and m.name.startswith(prefix + "src/hyprstudio/"):
                z.writestr(m.name[len(prefix + "src/"):], tar.extractfile(m).read())
        z.writestr("__main__.py", "import sys\nfrom hyprstudio.__main__ import main\nsys.exit(main())\n")
    return b"#!/usr/bin/env python3\n" + buf.getvalue()


def version_dir(tarball: Path) -> Path:
    """installer/_old/<Version>/ – vollständig: Install.sh, Portable.sh, uninstall.sh, Starter, arch/, portable/."""
    ver = tarball.name[len("labtoso-hyprstudio-"):-len(".tar.gz")]
    d = OLD / ver
    (d / "arch").mkdir(parents=True, exist_ok=True)
    (d / "portable").mkdir(parents=True, exist_ok=True)
    prefix = f"labtoso-hyprstudio-{ver}/"
    with tarfile.open(tarball) as tar:
        def pk(name: str) -> bytes:
            return tar.extractfile(prefix + "packaging/" + name).read()
        (d / "arch" / "PKGBUILD").write_bytes(lf(pk("PKGBUILD")))
        (d / "arch" / "install.sh").write_bytes(lf(pk("install.sh")))
        (d / "uninstall.sh").write_bytes(lf(pk("uninstall.sh")))
        (d / "portable" / "Hypr-Studio.pyz").write_bytes(_pyz_from_tar(tar, prefix))
    write_lf(d / "Install.sh", INSTALL_SH)
    write_lf(d / "Portable.sh", PORTABLE_SH)
    write_lf(d / "Hypr Studio.desktop", PORTABLE_DESKTOP)
    return d


def archive_versions() -> None:
    """Alle Versionen nach installer/_old/<Version>/; in installer/arch/ bleibt nur die aktuelle."""
    current = INST / "arch" / f"{NAME}.tar.gz"
    for tb in sorted((INST / "arch").glob("labtoso-hyprstudio-*.tar.gz")):
        d = version_dir(tb)
        if tb == current:
            shutil.copy2(tb, d / "arch" / tb.name)
        else:  # verschieben, nicht löschen (eine vorhandene Kopie derselben Version wird ersetzt)
            os.replace(tb, d / "arch" / tb.name)
    n = len([p for p in OLD.iterdir() if p.is_dir()])
    print(f"installer/_old/: {n} Versionen (neueste {VER})")


def release_zip(d: Path) -> Path:
    """GitHub-Release: nur Install.sh, uninstall.sh und der .desktop-Starter. Install.sh trägt das Paket
    (arch/: PKGBUILD, install.sh, Quellen) als Anhang in sich, damit sonst nichts im Zip liegt."""
    import base64
    ver = d.name
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w:gz") as tar:
        for f in sorted((d / "arch").rglob("*")):
            if f.is_file():
                ti = tarfile.TarInfo("arch/" + f.relative_to(d / "arch").as_posix())
                ti.size = f.stat().st_size
                ti.mode = 0o755 if f.name in EXEC else 0o644
                ti.mtime = int(f.stat().st_mtime)
                tar.addfile(ti, io.BytesIO(f.read_bytes()))
    payload = base64.encodebytes(buf.getvalue())
    script = lf(SELF_INSTALL_SH.replace("{ver}", ver).encode("utf-8")) + payload
    rel = DIST / "releases"
    rel.mkdir(parents=True, exist_ok=True)
    target = rel / f"HyprStudio-{ver}.zip"
    files = (("Install.sh", script, 0o755), ("uninstall.sh", lf((d / "uninstall.sh").read_bytes()), 0o755),
             ("Install Hypr Studio.desktop", lf(RELEASE_DESKTOP.encode("utf-8")), 0o755))
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED) as z:
        for name, data, mode in files:
            zi = zipfile.ZipInfo(f"HyprStudio-{ver}/{name}", (2026, 1, 1, 0, 0, 0))
            zi.external_attr = (mode | 0o100000) << 16
            zi.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(zi, data)
    return target


SELF_INSTALL_SH = """#!/bin/sh
# Install Hypr Studio {ver} – self-contained: the package (PKGBUILD, install.sh, sources) is attached below
set -e
TMP="$(mktemp -d /tmp/hyprstudio-setup.XXXXXX)"
sed '1,/^__HYPRSTUDIO_PAYLOAD__$/d' "$0" | base64 -d | tar -xzf - -C "$TMP"
sh "$TMP/arch/install.sh" "$@"
exit $?
__HYPRSTUDIO_PAYLOAD__
"""

# Doppelklick-Starter im Release: installiert im Terminal (fragt nach dem Passwort)
RELEASE_DESKTOP = """[Desktop Entry]
Type=Application
Name=Install Hypr Studio
Comment=Installs Hypr Studio (asks for your password)
Exec=sh -c 'cd "$(dirname "%k")" && sh Install.sh; echo; echo Press Enter to close; read x'
Icon=system-software-install
Terminal=true
Categories=Settings;
"""

INSTALL_SH = """#!/bin/sh
# Install Hypr Studio (app menu entry and icon)
exec sh "$(cd "$(dirname "$0")" && pwd)/arch/install.sh" "$@"
"""

PORTABLE_SH = """#!/bin/sh
# Start Hypr Studio without installing (installs only PySide6 if missing)
HERE="$(cd "$(dirname "$0")" && pwd)"
if ! python3 -c "import PySide6" 2>/dev/null && ! python3 -c "import PyQt6" 2>/dev/null; then
  echo "Qt for Python is missing – installing it …"
  # do not start sudo from the cloud folder (root cannot read FUSE folders)
  cd /tmp || cd /
  if command -v pacman >/dev/null; then sudo pacman -S --needed --noconfirm pyside6
  elif command -v apt-get >/dev/null; then sudo apt-get install -y python3-pyqt6
  elif command -v dnf >/dev/null; then sudo dnf install -y python3-pyside6
  elif command -v zypper >/dev/null; then sudo zypper -n in python3-pyside6
  fi
fi
exec python3 "$HERE/portable/Hypr-Studio.pyz" "$@"
"""

# Doppelklick-Starter (relativ zum Ordner über %k), Terminal für die evtl. nötige Qt-Installation
PORTABLE_DESKTOP = """[Desktop Entry]
Type=Application
Name=Hypr Studio (portable)
Exec=sh -c 'cd "$(dirname "%k")" && sh Portable.sh'
Icon=preferences-desktop-theme
Terminal=false
Categories=Settings;
"""


if __name__ == "__main__":
    render_icons()
    pyz = build_pyz()
    tb = build_tarball()
    build_installer(pyz, tb)
    for d in sorted(p for p in OLD.iterdir() if p.is_dir()):
        release_zip(d)
    print("dist/releases/: Zips nur mit Install.sh, uninstall.sh, .desktop")
