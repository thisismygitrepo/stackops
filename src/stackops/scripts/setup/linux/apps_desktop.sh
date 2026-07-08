#!/usr/bin/bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
STACKOPS_REPO_DIR="$(cd -- "$SCRIPT_DIR/../../../../.." && pwd)"
read -r DISTRIBUTION_ID PACKAGE_MANAGER < <(
    cd "$STACKOPS_REPO_DIR"
    PYTHONPATH="$STACKOPS_REPO_DIR/src" uv run --no-project python -m stackops.utils.installer_utils.linux_package_manager
)
if [[ "$PACKAGE_MANAGER" == "dnf" && "$DISTRIBUTION_ID" != "fedora" ]]; then
    echo "Desktop package installation on $DISTRIBUTION_ID requires explicit EPEL/CRB repository configuration." >&2
    exit 1
fi


echo """📧 EMAIL CLIENT | Installing Thunderbird"""
echo "📥 Installing Thunderbird via Flatpak..."
flatpak install flathub org.mozilla.Thunderbird


echo """✏️ SCREEN ANNOTATION | Installing Gromit-MPX"""
echo "📥 Installing Gromit-MPX via Flatpak..."
flatpak install net.christianbeier.Gromit-MPX

echo """📋 CLIPBOARD MANAGERS | Installing CopyQ"""
echo "📥 Installing CopyQ via Flatpak..."
flatpak install flathub com.github.hluk.copyq --noninteractive

echo """🔗 REMOTE DESKTOP | Installing Remmina"""
echo "📥 Installing Remmina and RDP plugin..."
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo apt-get update
    sudo apt-get install -y remmina remmina-plugin-rdp
else
    sudo dnf install -y remmina remmina-plugins-rdp
fi

# Alternative Remmina installation via flatpak (reference)
# echo "📥 Setting up Flatpak repositories..."
# flatpak remote-add --user --if-not-exists flathub https://flathub.org/repo/flathub.flatpakrepo
# flatpak install org.freedesktop.Platform
# flatpak install org.freedesktop.Platform.openh264
# flatpak install --user flathub org.remmina.Remmina
# flatpak run --user org.remmina.Remmina

echo """🚀 APPLICATION LAUNCHER | Installing Rofi
"""
echo "📥 Installing Rofi application launcher..."
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo apt-get install -y rofi
else
    sudo dnf install -y rofi
fi

echo """📎 CLIPBOARD HISTORY | Installing Greenclip
"""
# Session type detection (reference)
# session_type=$(echo $XDG_SESSION_TYPE)
# if [ "$session_type" == "x11" ]; then
#     echo "Detected X11 session. Installing X11-related packages and tools..."
#     sudo apt-get install -y xdotool xsel xclip
# elif [ "$session_type" == "wayland" ]; then
#     echo "Detected Wayland session. Installing Wayland-related packages and tools..."
#     sudo apt-get install -y wl-clipboard wtype
# else
#     echo "Unknown session type: $session_type"
#     exit 1
# fi

echo "📥 Downloading and installing Greenclip clipboard manager..."
wget -P ~/Downloads https://github.com/erebe/greenclip/releases/download/v4.2/greenclip
chmod +x ~/Downloads/greenclip
sudo mv ~/Downloads/greenclip /usr/bin/

echo "ℹ️ Usage instructions:"
echo "- Start daemon: greenclip daemon &"
echo "- With Rofi: rofi -modi \"clipboard:greenclip print\" -show clipboard -run-command '{cmd}'"
echo "- For emoji picker: rofi -modi \"emoji:rofimoji\" -show emoji"
echo "- Application launcher: rofi -show drun"

echo """🔄 APPLICATION LINKING | Linking applications to user space
"""
echo "🔗 Creating application symlinks..."
ln -s /home/$USER/.nix-profile/share/applications/* /home/$USER/.local/share/applications/

echo """✅ INSTALLATION COMPLETE | Desktop applications have been installed
"""
#!/bin/bash
# 🖥️ GUI APPLICATIONS AND DESKTOP ENVIRONMENT SETUP SCRIPT
# This script installs graphical user interfaces and desktop environments

echo """📦 INSTALLING GUI COMPONENTS | Setting up desktop environment
"""

# echo "📥 Installing Nautilus file manager..."
# sudo apt-get install -y nautilus  # 📂 graphical file manager
# sudo apt-get install -y x11-apps  # 🎨 few graphical test apps like xeyes

echo "📥 Installing XRDP - Remote Desktop Protocol server..."
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo apt-get install -y xrdp
else
    sudo dnf install -y xrdp
fi

# echo "📥 Installing X.Org server and components..."
# sudo apt-get install -y xorg  # 🎯 xorg server
# sudo apt-get install -y xinit  # 🚀 xorg init
# sudo apt-get install -y xserver-xorg  # 🖼️ xorg server

echo "📥 Installing XFCE4 desktop environment..."
if [[ "$PACKAGE_MANAGER" == "apt" ]]; then
    sudo apt-get install -y xfce4 xfce4-goodies
else
    sudo dnf install -y @xfce-desktop-environment
fi

echo """🔧 CONFIGURING XRDP | Setting up Remote Desktop service
"""
