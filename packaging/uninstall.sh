#!/bin/sh
# Uninstall Hypr Studio (Arch: pacman package, otherwise the files install.sh created in /usr)
# Optional: remove the include from the Hyprland config and restore the original Waybar files.

CFG="${XDG_CONFIG_HOME:-$HOME/.config}"
MARK="Hypr Studio (LabtosoStudios)"

echo "==> Uninstalling Hypr Studio"
# do not start sudo/pacman from inside the cloud folder (root cannot read FUSE folders)
cd /tmp 2>/dev/null || cd /

if command -v pacman >/dev/null 2>&1 && pacman -Qi labtoso-hyprstudio >/dev/null 2>&1; then
  sudo pacman -R --noconfirm labtoso-hyprstudio
elif [ -d /usr/lib/labtoso-hyprstudio ] || [ -f /usr/bin/hypr-studio ]; then
  sudo sh -c '
    rm -rf /usr/lib/labtoso-hyprstudio
    rm -f /usr/bin/hypr-studio /usr/bin/l-launcher
    rm -f /usr/share/applications/de.labtosostudios.hyprstudio.desktop
    rm -f /usr/share/icons/hicolor/scalable/apps/de.labtosostudios.hyprstudio.svg
    for s in 16 32 48 64 128 256; do
      rm -f "/usr/share/icons/hicolor/${s}x${s}/apps/de.labtosostudios.hyprstudio.png"
    done
    gtk-update-icon-cache -q /usr/share/icons/hicolor 2>/dev/null || true
  '
else
  echo "    Not installed (the portable version needs no uninstall)"
fi

printf "Restore your own Hyprland, Waybar and launcher settings? [y/N] "
read -r ans
case "$ans" in
  j|J|y|Y)
    # Remove the include from hyprland.lua / hyprland.conf (only our two lines)
    for f in "$CFG/hypr/hyprland.lua" "$CFG/hypr/hyprland.conf"; do
      [ -f "$f" ] || continue
      if grep -q "hyprstudio" "$f"; then
        cp "$f" "$f.before-uninstall"
        sed -i -e "/^[#-]* *$MARK$/d" -e "/^[#-]* *$MARK – Laptop-Tasten$/d" -e "/^[#-]* *$MARK – Leistung$/d" -e "/^[#-]* *$MARK – Hell\/Dunkel$/d" \
               -e '/^require("hyprstudio")$/d' -e '/^require("hyprstudio_laptop")$/d' -e '/^require("hyprstudio_perf")$/d' -e '/^require("hyprstudio_look")$/d' \
               -e '\#^source = ~/.config/hypr/hyprstudio.conf$#d' -e '\#^source = ~/.config/hypr/hyprstudio_laptop.conf$#d' -e '\#^source = ~/.config/hypr/hyprstudio_perf.conf$#d' -e '\#^source = ~/.config/hypr/hyprstudio_look.conf$#d' "$f"
        echo "    Include removed: $f (copy: $f.before-uninstall)"
      fi
    done
    # Kitty: remove the hyprstudio.conf include from kitty.conf
    f="$CFG/kitty/kitty.conf"
    if [ -f "$f" ] && grep -q "^include hyprstudio.conf$" "$f"; then
        cp "$f" "$f.before-uninstall"
        sed -i -e "/^# $MARK$/d" -e '/^include hyprstudio.conf$/d' "$f"
        echo "    Include removed: $f"
    fi
    # Copy the originals back (Waybar, Rofi, Wofi, Fuzzel, Hyprlock, KDE colours) – the generated files stay next to them as *.hyprstudio
    for n in waybar/config.jsonc waybar/config.json waybar/config waybar/style.css              rofi/config.rasi wofi/config wofi/style.css fuzzel/fuzzel.ini hypr/hyprlock.conf kdeglobals; do
      f="$CFG/$n"
      if [ -f "$f.hyprstudio-original" ]; then
        [ -f "$f" ] && cp "$f" "$f.hyprstudio"
        cp "$f.hyprstudio-original" "$f"
        echo "    Original restored: $f"
      fi
    done
    command -v hyprctl >/dev/null && hyprctl reload >/dev/null 2>&1
    if pgrep -x waybar >/dev/null; then
      pkill -x waybar; sleep 0.3
      (waybar >/dev/null 2>&1 &)
    fi
    ;;
esac

echo "==> Done"
