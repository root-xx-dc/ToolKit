#!/usr/bin/env bash
# ROOT//X TOOLKIT — Linux/macOS installer
# Compatible with: Debian/Ubuntu, Kali, Arch, Fedora, CachyOS, macOS
set -e

CYAN='\033[96m'
GREEN='\033[92m'
YELLOW='\033[93m'
RED='\033[91m'
RESET='\033[0m'
BOLD='\033[1m'

header() {
    echo ""
    echo -e "${CYAN}${BOLD}  ============================================${RESET}"
    echo -e "${CYAN}${BOLD}    ROOT//X TOOLKIT -- Setup${RESET}"
    echo -e "${CYAN}${BOLD}  ============================================${RESET}"
    echo ""
}

ok()   { echo -e " ${GREEN}[OK]${RESET} $*"; }
info() { echo -e " ${CYAN}[*]${RESET} $*"; }
warn() { echo -e " ${YELLOW}[!]${RESET} $*"; }
err()  { echo -e " ${RED}[!]${RESET} $*"; }

header

# -- 1. Python ----------------------------------------------------------------
PYTHON=""
for candidate in python3 python; do
    if command -v "$candidate" &>/dev/null; then
        VER=$("$candidate" -c 'import sys; print(sys.version_info >= (3,8))' 2>/dev/null)
        if [ "$VER" = "True" ]; then
            PYTHON="$candidate"
            break
        fi
    fi
done

if [ -z "$PYTHON" ]; then
    err "Python 3.8+ not found."
    echo ""
    echo "  Install Python:"
    echo "    Debian/Ubuntu/Kali : sudo apt install python3 python3-pip"
    echo "    Arch/CachyOS       : sudo pacman -S python python-pip"
    echo "    Fedora/RHEL        : sudo dnf install python3 python3-pip"
    echo "    macOS              : brew install python"
    exit 1
fi
ok "Python: $($PYTHON --version)"

# -- 2. pip -------------------------------------------------------------------
HAS_PIP=false
if "$PYTHON" -m pip --version &>/dev/null; then
    HAS_PIP=true
elif command -v pip3 &>/dev/null; then
    HAS_PIP=true
fi

if [ "$HAS_PIP" = false ]; then
    info "pip not found, attempting ensurepip..."
    if "$PYTHON" -m ensurepip --default-pip &>/dev/null 2>&1; then
        HAS_PIP=true
        ok "pip installed via ensurepip."
    else
        err "pip not found and ensurepip failed."
        echo ""
        echo "  Install pip:"
        echo "    Debian/Ubuntu/Kali : sudo apt install python3-pip"
        echo "    Arch/CachyOS       : sudo pacman -S python-pip"
        echo "    Fedora/RHEL        : sudo dnf install python3-pip"
        exit 1
    fi
fi
ok "pip: $($PYTHON -m pip --version 2>/dev/null | awk '{print $1,$2}')"

# -- 3. Install package -------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
info "Installing package from: $SCRIPT_DIR"

# Build binary protected modules if build_protected.py is present
if [ -f "$SCRIPT_DIR/build_protected.py" ]; then
    "$PYTHON" "$SCRIPT_DIR/build_protected.py" 2>/dev/null || true
fi

# Try normal install first, then with --break-system-packages for newer distros
if "$PYTHON" -m pip install -e "$SCRIPT_DIR" --quiet 2>/dev/null; then
    ok "Package installed."
elif "$PYTHON" -m pip install -e "$SCRIPT_DIR" --quiet --break-system-packages 2>/dev/null; then
    ok "Package installed (with --break-system-packages)."
else
    # Last resort: install to user directory
    if "$PYTHON" -m pip install -e "$SCRIPT_DIR" --quiet --user 2>/dev/null; then
        ok "Package installed (user mode)."
    else
        err "pip install failed. Try running with sudo or inside a virtualenv."
        exit 1
    fi
fi

# -- 4. Check if 'rootx' is in PATH ------------------------------------------
ROOTX_BIN=$(command -v rootx 2>/dev/null || true)
if [ -z "$ROOTX_BIN" ]; then
    warn "'rootx' is not yet in PATH."

    # Find pip scripts directory
    USER_BIN="$($PYTHON -c 'import site,os; d=site.getusersitepackages(); print(os.path.join(os.path.dirname(d),"bin"))' 2>/dev/null || true)"

    # Add to shell config if not already there
    SHELL_RC=""
    if [ -f "$HOME/.zshrc" ]; then
        SHELL_RC="$HOME/.zshrc"
    elif [ -f "$HOME/.bashrc" ]; then
        SHELL_RC="$HOME/.bashrc"
    elif [ -f "$HOME/.profile" ]; then
        SHELL_RC="$HOME/.profile"
    fi

    if [ -n "$USER_BIN" ] && [ -d "$USER_BIN" ]; then
        if [ -n "$SHELL_RC" ]; then
            EXPORT_LINE="export PATH=\"\$PATH:$USER_BIN\""
            if ! grep -qF "$USER_BIN" "$SHELL_RC" 2>/dev/null; then
                echo "" >> "$SHELL_RC"
                echo "# ROOT//X TOOLKIT -- added by installer" >> "$SHELL_RC"
                echo "$EXPORT_LINE" >> "$SHELL_RC"
                ok "Added $USER_BIN to PATH in $SHELL_RC"
            else
                ok "$USER_BIN already in $SHELL_RC"
            fi
        fi
        export PATH="$PATH:$USER_BIN"
    fi
fi

if command -v rootx &>/dev/null; then
    ok "Command 'rootx' available at: $(command -v rootx)"
else
    warn "Run: source ~/.bashrc  (or open a new terminal) to activate the 'rootx' command"
fi

# -- 5. Desktop shortcut (Linux only) ----------------------------------------
if [[ "$OSTYPE" != "darwin"* ]]; then
    DESKTOP_DIR="$HOME/Desktop"
    if command -v xdg-user-dir &>/dev/null; then
        DESKTOP_DIR=$(xdg-user-dir DESKTOP 2>/dev/null || echo "$HOME/Desktop")
    fi

    TERMINAL=""
    for t in gnome-terminal konsole xterm xfce4-terminal lxterminal tilix kitty alacritty; do
        if command -v "$t" &>/dev/null; then
            TERMINAL="$t"
            break
        fi
    done

    if [ -n "$TERMINAL" ] && [ -d "$DESKTOP_DIR" ]; then
        SHORTCUT="$DESKTOP_DIR/RootX-Toolkit.desktop"

        case "$TERMINAL" in
            gnome-terminal)  EXEC="gnome-terminal -- bash -c 'rootx; exec bash'" ;;
            konsole)         EXEC="konsole -e bash -c 'rootx; exec bash'" ;;
            xfce4-terminal)  EXEC="xfce4-terminal -e \"bash -c 'rootx; exec bash'\"" ;;
            lxterminal)      EXEC="lxterminal -e \"bash -c 'rootx; exec bash'\"" ;;
            tilix)           EXEC="tilix -e bash -c 'rootx; exec bash'" ;;
            kitty)           EXEC="kitty bash -c 'rootx; exec bash'" ;;
            alacritty)       EXEC="alacritty -e bash -c 'rootx; exec bash'" ;;
            *)               EXEC="$TERMINAL -e \"bash -c 'rootx; exec bash'\"" ;;
        esac

        cat > "$SHORTCUT" <<DESKTOPEOF
[Desktop Entry]
Version=1.0
Type=Application
Name=ROOT//X TOOLKIT
Comment=ROOT//X Toolkit
Exec=$EXEC
Icon=utilities-terminal
Terminal=false
Categories=System;Utility;
StartupNotify=true
DESKTOPEOF
        chmod +x "$SHORTCUT"

        if command -v gio &>/dev/null; then
            gio set "$SHORTCUT" metadata::trusted true 2>/dev/null || true
        fi

        ok "Desktop shortcut: $SHORTCUT"
    fi
fi

# macOS shortcut
if [[ "$OSTYPE" == "darwin"* ]]; then
    APP_SCRIPT="$HOME/Applications/RootX-Toolkit.command"
    mkdir -p "$HOME/Applications"
    echo '#!/bin/bash' > "$APP_SCRIPT"
    echo 'rootx' >> "$APP_SCRIPT"
    chmod +x "$APP_SCRIPT"
    ok "macOS shortcut: $APP_SCRIPT"
fi

# -- 6. Clear license cache --------------------------------------------------
info "Clearing license cache..."
if [[ "$OSTYPE" == "darwin"* ]]; then
    CACHE_DIR="$HOME/Library/Application Support/rootx-toolkit"
else
    CACHE_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/rootx-toolkit"
fi

if [ -f "$CACHE_DIR/license_cache.bin" ] || [ -f "$CACHE_DIR/license_cache.json" ]; then
    rm -f "$CACHE_DIR/license_cache.bin" "$CACHE_DIR/license_cache.json"
    ok "License cache cleared."
else
    ok "No cache found, skipping."
fi

# -- 7. Done ------------------------------------------------------------------
echo ""
echo -e "${GREEN}${BOLD}  ============================================${RESET}"
echo -e "${GREEN}${BOLD}    Setup complete!${RESET}"
echo -e "${GREEN}${BOLD}${RESET}"
echo -e "${GREEN}${BOLD}    Run:  rootx${RESET}"
echo -e "${GREEN}${BOLD}    or click the desktop shortcut${RESET}"
echo -e "${GREEN}${BOLD}  ============================================${RESET}"
echo ""
