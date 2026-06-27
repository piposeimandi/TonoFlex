#!/usr/bin/env bash
# Build a .deb package for TonoFlex
set -e

APP_DIR="$(cd "$(dirname "$0")" && pwd)"
VERSION="1.0.0"
PACKAGE="tonoflex"
ARCH="all"
BUILD_DIR="/tmp/${PACKAGE}_${VERSION}_${ARCH}"

echo "==> Limpiando build anterior..."
rm -rf "$BUILD_DIR"

echo "==> Creando estructura..."
mkdir -p "$BUILD_DIR/DEBIAN"
mkdir -p "$BUILD_DIR/usr/bin"
mkdir -p "$BUILD_DIR/usr/share/applications"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/64x64/apps"
mkdir -p "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps"
mkdir -p "$BUILD_DIR/usr/share/$PACKAGE"
mkdir -p "$BUILD_DIR/usr/share/doc/$PACKAGE"

echo "==> Copiando aplicación..."
cp "$APP_DIR/pitch_shifter_app.py" "$BUILD_DIR/usr/share/$PACKAGE/"
cp "$APP_DIR/pitch-shifter.png" "$BUILD_DIR/usr/share/icons/hicolor/64x64/apps/tonoflex.png"
cp "$APP_DIR/pitch-shifter.svg" "$BUILD_DIR/usr/share/icons/hicolor/scalable/apps/tonoflex.svg"

echo "==> Creando launcher en /usr/bin..."
cat > "$BUILD_DIR/usr/bin/tonoflex" << 'LAUNCHER'
#!/usr/bin/env bash
APP_DIR="/usr/share/tonoflex"
VENV_DIR="/usr/share/tonoflex/venv"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --quiet customtkinter pydub pygame pyrubberband numpy resampy librosa soundfile yt-dlp 2>/dev/null
fi

exec "$VENV_DIR/bin/python" "$APP_DIR/pitch_shifter_app.py"
LAUNCHER
chmod +x "$BUILD_DIR/usr/bin/tonoflex"

echo "==> Creando desktop entry..."
cat > "$BUILD_DIR/usr/share/applications/tonoflex.desktop" << DESKTOP
[Desktop Entry]
Type=Application
Name=TonoFlex
Comment=Ajuste de tono de audio/video sin cambiar la velocidad
Exec=tonoflex
Icon=tonoflex
Terminal=false
Categories=AudioVideo;Audio;Music;
StartupNotify=true
DESKTOP

echo "==> Creando control file..."
cat > "$BUILD_DIR/DEBIAN/control" << CONTROL
Package: tonoflex
Version: $VERSION
Section: sound
Priority: optional
Architecture: $ARCH
Depends: python3 (>= 3.11), python3-venv, python3-pip, ffmpeg
Maintainer: TonoFlex
Description: Ajuste de tono de audio/video sin cambiar la velocidad
 Soporta carga de archivos, descarga desde YouTube,
 pitch shifting en tiempo real, normalización, y exportación.
CONTROL

echo "==> Creando postinst..."
cat > "$BUILD_DIR/DEBIAN/postinst" << 'POSTINST'
#!/bin/sh
set -e

APP_DIR="/usr/share/tonoflex"
VENV_DIR="$APP_DIR/venv"

case "$1" in
    configure)
        echo "Configurando TonoFlex..."

        if [ -n "$SUDO_USER" ]; then
            USER_HOME=$(getent passwd "$SUDO_USER" | cut -d: -f6)
        elif [ -n "$USER" ]; then
            USER_HOME="$HOME"
        else
            USER_HOME="$HOME"
        fi

        mkdir -p "$USER_HOME/descargas" "$USER_HOME/convertidos" 2>/dev/null || true

        if [ ! -d "$VENV_DIR" ]; then
            echo "  Creando entorno virtual..."
            python3 -m venv "$VENV_DIR"
        fi

        echo "  Instalando dependencias Python..."
        "$VENV_DIR/bin/pip" install --quiet --upgrade pip
        "$VENV_DIR/bin/pip" install --quiet \
            customtkinter \
            pydub \
            pygame \
            pyrubberband \
            numpy \
            resampy \
            librosa \
            soundfile \
            yt-dlp 2>&1 | tail -3

        # Refresh icon cache
        if command -v gtk-update-icon-cache >/dev/null 2>&1; then
            gtk-update-icon-cache /usr/share/icons/hicolor -f 2>/dev/null || true
        fi
        if command -v update-desktop-database >/dev/null 2>&1; then
            update-desktop-database 2>/dev/null || true
        fi

        echo "  ¡Listo!"
        ;;
esac
POSTINST
chmod +x "$BUILD_DIR/DEBIAN/postinst"

echo "==> Construyendo .deb..."
fakeroot dpkg-deb --build "$BUILD_DIR" "$APP_DIR/${PACKAGE}_${VERSION}_${ARCH}.deb"

echo ""
echo "Package creado: ${PACKAGE}_${VERSION}_${ARCH}.deb"
echo ""
echo "Para instalar:"
echo "  sudo dpkg -i ${PACKAGE}_${VERSION}_${ARCH}.deb"
echo "  sudo apt install -f"
