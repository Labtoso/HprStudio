#!/bin/sh
# Install Hypr Studio system-wide (Arch: as a pacman package, otherwise to /usr)
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
TARBALL="$(ls "$HERE"/labtoso-hyprstudio-*.tar.gz | sort -V | tail -n1)"

need_qt() {
  python3 -c "import PySide6" 2>/dev/null || python3 -c "import PyQt6" 2>/dev/null
}

if command -v pacman >/dev/null 2>&1 && command -v makepkg >/dev/null 2>&1 && [ "$(id -u)" -ne 0 ]; then
  echo "==> Arch detected: building pacman package"
  BUILD="$(mktemp -d)"
  cp "$HERE/PKGBUILD" "$TARBALL" "$BUILD/"
  (cd "$BUILD" && makepkg -sf --noconfirm)
  sudo pacman -U --noconfirm "$BUILD"/labtoso-hyprstudio-*.pkg.tar.zst
  echo "==> Done: Hypr Studio is in your app menu"
  exit 0
fi

if [ "$(id -u)" -ne 0 ]; then
  exec sudo sh "$0" "$@"
fi

echo "==> Installing to /usr"
if ! need_qt; then
  if command -v apt-get >/dev/null; then apt-get install -y python3-pyqt6 || apt-get install -y python3-pyside6.qtwidgets
  elif command -v dnf >/dev/null; then dnf install -y python3-pyside6
  elif command -v zypper >/dev/null; then zypper -n in python3-pyside6
  elif command -v pacman >/dev/null; then pacman -S --needed --noconfirm pyside6
  fi
fi
TMP="$(mktemp -d)"
tar -xzf "$TARBALL" -C "$TMP"
SRC="$(ls -d "$TMP"/labtoso-hyprstudio-*)"
install -d /usr/lib/labtoso-hyprstudio
cp -r "$SRC/src/hyprstudio" /usr/lib/labtoso-hyprstudio/
install -Dm755 "$SRC/packaging/hypr-studio" /usr/bin/hypr-studio
install -Dm644 "$SRC/packaging/de.labtosostudios.hyprstudio.desktop" /usr/share/applications/de.labtosostudios.hyprstudio.desktop
install -Dm644 "$SRC/src/hyprstudio/assets/hyprstudio.svg" /usr/share/icons/hicolor/scalable/apps/de.labtosostudios.hyprstudio.svg
for s in 16 32 48 64 128 256; do
  install -Dm644 "$SRC/packaging/icons/$s.png" "/usr/share/icons/hicolor/${s}x${s}/apps/de.labtosostudios.hyprstudio.png"
done
gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
echo "==> Done: Hypr Studio is in your app menu"
