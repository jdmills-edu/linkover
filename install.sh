#!/usr/bin/env bash
set -euo pipefail

echo "==> Installing Linkover..."

# If running inside a Flatpak sandbox (e.g. VSCodium), delegate everything to
# the host shell so the venv is built with the real system Python, not the
# Flatpak-bundled one.  The shebang in the installed script must resolve on
# the host, which it won't if the venv uses the Flatpak's interpreter.
if [ -n "${FLATPAK_ID:-}" ]; then
    echo "    (detected Flatpak environment — delegating to host shell)"
    exec flatpak-spawn --host bash "$(realpath "$0")" "$@"
fi

# pipx is the cleanest way to install Python CLI apps on immutable distros.
# It gives linkover its own isolated virtualenv while making the binary
# available on PATH via ~/.local/bin.
if ! python3 -m pipx --version &>/dev/null; then
    echo "pipx not found — installing via pip..."
    pip install --user pipx
    python3 -m pipx ensurepath
    echo "Restart your shell or run: source ~/.bashrc"
fi

# --system-site-packages lets the venv reach the system gi/PyGObject,
# which is installed by GNOME and can't be pip-installed cleanly.
PIPX_HOME="$HOME/.local/pipx" \
PIPX_BIN_DIR="$HOME/.local/bin" \
python3 -m pipx install --force --system-site-packages "$(dirname "$(realpath "$0")")"

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
