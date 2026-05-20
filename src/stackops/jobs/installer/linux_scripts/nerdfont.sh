#!/usr/bin/env bash
set -euo pipefail

# Installs CascadiaCode Nerd Font on Linux.

FONT_SOURCE_DIR="${NERDFONT_SOURCE_DIR:?NERDFONT_SOURCE_DIR must point to the extracted Nerd Fonts package}"
FONT_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fonts"
VERIFY_HINT="fc-list | grep CaskaydiaCove"

if [ ! -d "$FONT_SOURCE_DIR" ]; then
    echo "Nerd Fonts source directory does not exist: $FONT_SOURCE_DIR" >&2
    exit 1
fi

echo """📦 PREPARED | Using CascadiaCode Nerd Font payload for Linux
"""
echo "📂 Source directory: $FONT_SOURCE_DIR"

echo """🔧 INSTALLING | Setting up font files
"""
echo "📁 Creating fonts directory: $FONT_DIR"
mkdir -p "$FONT_DIR"

echo "📋 Copying font files to fonts directory..."
FONT_COUNT="$(find "$FONT_SOURCE_DIR" -type f \( -name "*.ttf" -o -name "*.otf" \) -print | wc -l | tr -d ' ')"
if [ "$FONT_COUNT" = "0" ]; then
    echo "No .ttf or .otf files were found in the prepared Nerd Fonts payload." >&2
    exit 1
fi

find "$FONT_SOURCE_DIR" -type f \( -name "*.ttf" -o -name "*.otf" \) -exec cp -f {} "$FONT_DIR" \;

if command -v fc-cache >/dev/null 2>&1; then
    echo "🔄 Updating font cache..."
    fc-cache -f -v "$FONT_DIR"
else
    echo "⚠️ fc-cache not found; skipping font cache refresh."
fi

echo """✅ INSTALLATION COMPLETE | CascadiaCode Nerd Font has been installed
"""
echo "ℹ️ To verify installation, run: $VERIFY_HINT"
echo "💡 USE 'CaskaydiaCove Nerd Font' in VS Code and other applications"
echo "🔄 You may need to restart applications to see the new font"
