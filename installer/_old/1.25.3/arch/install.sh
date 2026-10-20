#!/bin/sh
# Install Hypr Studio system-wide (Arch: as a pacman package, otherwise to /usr).
# Installs only Hypr Studio itself (+ PySide6 if missing) – Rofi, Wofi, Fuzzel, Waybar etc.
# can be installed from inside the app under More › Install.
set -e

# Copy everything to a local temp folder first and work there: if the installer lies in a
# cloud/FUSE folder (e.g. pCloud), root cannot read it → pacman would otherwise report
# "could not get current working directory".
if [ -z "$HS_WORK" ]; then
  HERE="$(cd "$(dirname "$0")" && pwd)"
  HS_WORK="$(mktemp -d /tmp/hyprstudio-install.XXXXXX)"
  cp "$HERE/PKGBUILD" "$HERE/install.sh" "$HS_WORK/"
  cp "$(ls "$HERE"/labtoso-hyprstudio-*.tar.gz | sort -V | tail -n1)" "$HS_WORK/"
fi
cd "$HS_WORK"
TARBALL="$(ls "$HS_WORK"/labtoso-hyprstudio-*.tar.gz | sort -V | tail -n1)"

need_qt() {
  python3 -c "import PySide6" 2>/dev/null || python3 -c "import PyQt6" 2>/dev/null
}

if command -v pacman >/dev/null 2>&1 && command -v makepkg >/dev/null 2>&1 && [ "$(id -u)" -ne 0 ]; then
  echo "==> Arch detected: building pacman package"
  makepkg -sf --noconfirm
  sudo pacman -U --noconfirm "$HS_WORK"/labtoso-hyprstudio-*.pkg.tar.zst
  echo "==> Done: Hypr Studio is in your app menu"
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  exec sudo env HS_WORK="$HS_WORK" sh "$HS_WORK/install.sh" "$@"
fi

echo "==> Installing to /usr"
if ! need_qt; then
  if command -v apt-get >/dev/null; then apt-get install -y python3-pyqt6 || apt-get install -y python3-pyside6.qtwidgets
  elif command -v dnf >/dev/null; then dnf install -y python3-pyside6
  elif command -v zypper >/dev/null; then zypper -n in python3-pyside6
  elif command -v pacman >/dev/null; then pacman -S --needed --noconfirm pyside6
  fi
fi
tar -xzf "$TARBALL" -C "$HS_WORK"
SRC="$(ls -d "$HS_WORK"/labtoso-hyprstudio-*/ | head -n1)"
install -d /usr/lib/labtoso-hyprstudio
cp -r "$SRC/src/hyprstudio" /usr/lib/labtoso-hyprstudio/
install -Dm755 "$SRC/packaging/hypr-studio" /usr/bin/hypr-studio
install -Dm755 "$SRC/packaging/l-launcher" /usr/bin/l-launcher
install -Dm644 "$SRC/packaging/de.labtosostudios.hyprstudio.desktop" /usr/share/applications/de.labtosostudios.hyprstudio.desktop
install -Dm644 "$SRC/src/hyprstudio/assets/hyprstudio.svg" /usr/share/icons/hicolor/scalable/apps/de.labtosostudios.hyprstudio.svg
for s in 16 32 48 64 128 256; do
  install -Dm644 "$SRC/packaging/icons/$s.png" "/usr/share/icons/hicolor/${s}x${s}/apps/de.labtosostudios.hyprstudio.png"
done
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
echo "==> Done: Hypr Studio is in your app menu"
