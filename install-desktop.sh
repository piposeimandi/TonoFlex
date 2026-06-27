#!/usr/bin/env bash
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
DESKTOP_FILE="$APP_DIR/pitch-shifter.desktop"
ICON_FILE="$APP_DIR/pitch-shifter.svg"
APP_ICONS="$HOME/.local/share/icons/hicolor/scalable/apps"
APP_ENTRIES="$HOME/.local/share/applications"

mkdir -p "$APP_ICONS" "$APP_ENTRIES"

# Install icon
cp "$ICON_FILE" "$APP_ICONS/pitch-shifter.svg"

# Install desktop entry (with portable paths)
sed "s|Exec=.*|Exec=$APP_DIR/run.sh|; s|Icon=.*|Icon=pitch-shifter|" \
    "$DESKTOP_FILE" > "$APP_ENTRIES/pitch-shifter.desktop"

chmod +x "$APP_ENTRIES/pitch-shifter.desktop"

echo "Instalado. Buscá 'Pitch Shifter' en el menú de aplicaciones."
echo ""
echo "Si no aparece, actualizá la cache con:"
echo "  update-desktop-database ~/.local/share/applications/"
