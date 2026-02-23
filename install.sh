#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Linkover..."

# pipx is the cleanest way to install Python CLI apps on immutable distros.
# It gives linkover its own isolated virtualenv while making the binary
# available on PATH via ~/.local/bin.
if ! command -v pipx &>/dev/null; then
    echo "pipx not found — installing via pip..."
    pip install --user pipx
    python3 -m pipx ensurepath
    echo "Restart your shell or run: source ~/.bashrc"
fi

pipx install --force "$(dirname "$0")"

echo "==> Installing icon..."
ICON_DIR="$HOME/.local/share/icons/hicolor/scalable/apps"
mkdir -p "$ICON_DIR"
cp "$(dirname "$0")/linkover/icons/linkover.svg" "$ICON_DIR/linkover.svg"
gtk-update-icon-cache -f -t "$HOME/.local/share/icons/hicolor" 2>/dev/null || true

echo ""
echo "==> Installing AppIndicator support for GNOME..."
echo "    Linkover needs the 'AppIndicator and KStatusNotifierItem Support' extension."
echo "    Install it from: https://extensions.gnome.org/extension/615/appindicator-support/"
echo "    (or via: gnome-extensions-app)"
echo ""

echo "==> Setting up autostart..."
AUTOSTART_DIR="$HOME/.config/autostart"
mkdir -p "$AUTOSTART_DIR"
cp "$(dirname "$0")/linkover.desktop" "$AUTOSTART_DIR/linkover.desktop"
sed -i "s|Exec=linkover|Exec=$HOME/.local/bin/linkover|" "$AUTOSTART_DIR/linkover.desktop"

echo ""
echo "==> Done! Run 'linkover' to complete first-time setup (Pushover login)."
echo "    It will start automatically on next login."
