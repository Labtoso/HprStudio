# Hypr Studio

**Style Hyprland, Waybar and your app launcher with a few clicks – no config editing needed.**

Hypr Studio is a dark, rounded desktop app for Linux (Python + PySide6) by **LabtosoStudios**. You pick presets, move sliders and toggle switches, see the result in a live preview, and press **Apply**. Hypr Studio writes its own config files, includes them in yours and backs up everything it touches.

> Starts in **English** by default – switch to **German** via the gear icon (top left).

---

## Features

### Hyprland
- **Presets** – Hyprland, Tokyo Night, Catppuccin, Nord, Gruvbox, Rosé Pine, Dracula, Glass, Minimal – plus your own presets (save, rename, export, import)
- **Windows** – gaps, borders, rounding, layout, smart gaps
- **Workspaces** – name, monitor, gaps and border per workspace
- **Colours & effects** – gradient borders, opacity, dimming, blur, shadows
- **Animations** – curve, speed, window and workspace styles, with preview playback
- **Input** – keyboard layout, mouse sensitivity, acceleration on/off, scroll direction, touchpad
- **Keyboard shortcuts** – record any combo (up to 4 keys, even **Super alone**), searchable action list, templates, “Open launcher” action, import from your existing config
- **System** – autostart (Waybar starts exactly once), monitor mode and scaling
- **Wallpaper (hyprpaper)** – per monitor, slideshow, library, **search & download online** (wallhaven, SFW only) with filters
- **Cursor (hyprcursor)** – search installed themes, **install new ones** from a catalogue sorted by rating, newest or downloads

### Waybar
- Presets, **drag & drop bar editor**, module options, colours and fonts, on/off switch

### Launcher
- **Rofi, Wofi, Fuzzel** and the built-in **L Launcher** – every launcher keeps its own settings
- Detects which launcher your shortcuts actually start and switches shortcuts + Waybar button when you change it
- Presets, position, size, colours, icons (follows your KDE/GTK icon theme)
- “Second press closes”, “search from name start”

### L Launcher (`l-launcher`)
A small launcher that only shows apps whose **name starts with what you type** – re-filtered on every key. Type `hy`, press Enter, Hypr Studio opens. Most-used apps come first.

### More
- **Repair** – reads `hyprctl configerrors` and fixes or comments out broken lines
- **Install / uninstall** helpers (Waybar, launchers, Kitty, hyprpaper, hyprcursor, fastfetch …)
- **Kitty** terminal styling incl. Fastfetch and own commands on start
- **Light / Dark** colour scheme for all apps (GTK + KDE), mouse & touchpad settings, backups browser

---

## Requirements
- Hyprland (Lua config `hyprland.lua` – the old `.conf` format can be chosen under **Settings › Advanced**; Hyprland 0.57+ only supports Lua)
- Python 3 and PySide6 (`sudo pacman -S pyside6`)
- Optional: waybar, rofi / wofi / fuzzel, kitty, hyprpaper, hyprcursor

## Installation
From the `installer/` folder:

| Way | How |
|---|---|
| Install (app menu entry + `hypr-studio`, `l-launcher`) | `sh installer/Installieren.sh` |
| Arch package | `cd installer/arch && makepkg -si` |
| Portable, no install | `sh installer/Portable.sh` |
| Uninstall | `sh installer/uninstall.sh` |

Every released version is kept complete in `installer/_old/<version>/` (install, uninstall, portable).

## Build
```bash
python build.py
python -m unittest discover -s tests
```
On Windows the app runs in **test mode** (writes only to a cache folder, runs no commands).

## Safety
- Your own config files are backed up before the first change (`*.hyprstudio-original` or time-stamped copies)
- **Undo** per area and **Reset everything** (gear menu) bring the original state back
- Backups can be restored under **More › Backups**

## License
MIT – © LabtosoStudios

