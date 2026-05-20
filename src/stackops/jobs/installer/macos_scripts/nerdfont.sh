#!/usr/bin/env bash
set -euo pipefail

# Installs CascadiaCode Nerd Font on macOS.

FONT_VERSION="${NERDFONT_VERSION:-latest}"
FONT_ARCHIVE="CascadiaCode.tar.xz"
if [ "$FONT_VERSION" = "latest" ]; then
    DOWNLOAD_URL="https://github.com/ryanoasis/nerd-fonts/releases/latest/download/${FONT_ARCHIVE}"
else
    case "$FONT_VERSION" in
        v*) RELEASE_TAG="$FONT_VERSION" ;;
        *) RELEASE_TAG="v$FONT_VERSION" ;;
    esac
    DOWNLOAD_URL="https://github.com/ryanoasis/nerd-fonts/releases/download/${RELEASE_TAG}/${FONT_ARCHIVE}"
fi
TMP_DIR="$(mktemp -d)"
FONT_DIR="$HOME/Library/Fonts"
VERIFY_HINT="system_profiler SPFontsDataType | grep -i CaskaydiaCove"

cleanup() {
    rm -rf "$TMP_DIR"
}
trap cleanup EXIT

echo """📥 DOWNLOADING | Fetching CascadiaCode Nerd Font for macOS
"""
echo "🔽 Downloading ${FONT_ARCHIVE}..."
curl -fL --retry 3 -o "$TMP_DIR/$FONT_ARCHIVE" "$DOWNLOAD_URL"

echo """📦 EXTRACTING | Unpacking font archive
"""
echo "📂 Extracting font files..."
tar -xf "$TMP_DIR/$FONT_ARCHIVE" -C "$TMP_DIR"

echo """🔧 INSTALLING | Setting up font files
"""
echo "📁 Creating fonts directory: $FONT_DIR"
mkdir -p "$FONT_DIR"

echo "📋 Copying font files to fonts directory..."
FONT_COUNT="$(find "$TMP_DIR" -maxdepth 1 -type f \( -name "*.ttf" -o -name "*.otf" \) -print | wc -l | tr -d ' ')"
if [ "$FONT_COUNT" = "0" ]; then
    echo "No .ttf or .otf files were found in the downloaded archive." >&2
    exit 1
fi

find "$TMP_DIR" -maxdepth 1 -type f \( -name "*.ttf" -o -name "*.otf" \) -exec cp -f {} "$FONT_DIR" \;

echo """✅ INSTALLATION COMPLETE | CascadiaCode Nerd Font has been installed
"""
echo "ℹ️ To verify installation, run: $VERIFY_HINT"
echo "💡 USE 'CaskaydiaCove Nerd Font' in VS Code and other applications"
echo "🔄 You may need to restart applications to see the new font"
