#!/bin/sh
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
