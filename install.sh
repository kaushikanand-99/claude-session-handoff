#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
#  csession — installer
#  Run from your project root:  bash install.sh
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

BOLD="\033[1m"
GREEN="\033[0;32m"
YELLOW="\033[0;33m"
RED="\033[0;31m"
RESET="\033[0m"

info()    { echo -e "${BOLD}[csession]${RESET} $*"; }
success() { echo -e "${GREEN}✅  $*${RESET}"; }
warn()    { echo -e "${YELLOW}⚠️   $*${RESET}"; }
error()   { echo -e "${RED}❌  $*${RESET}"; exit 1; }

echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo -e "${BOLD}  csession — Claude Code Session Manager${RESET}"
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
echo ""

# ── Check Python ──────────────────────────────────────────────────────────────
info "Checking Python 3..."
if ! command -v python3 &>/dev/null; then
    error "Python 3 is required. Install it from https://python.org"
fi
PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
success "Python $PYTHON_VERSION found"

# ── Optional: pyperclip for --copy support ────────────────────────────────────
info "Checking pyperclip (optional, for clipboard copy)..."
if python3 -c "import pyperclip" 2>/dev/null; then
    success "pyperclip already installed"
else
    warn "pyperclip not found. Installing (enables 'csession resume --copy')..."
    pip install pyperclip --quiet && success "pyperclip installed" || warn "pyperclip install failed — clipboard copy won't work, but everything else will"
fi

# ── Detect install mode ───────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CSESSION_SRC="$SCRIPT_DIR/csession.py"

if [[ ! -f "$CSESSION_SRC" ]]; then
    error "csession.py not found in $SCRIPT_DIR"
fi

echo ""
info "Where do you want to install csession?"
echo "  1) System-wide  → /usr/local/bin/csession   (all projects, needs sudo)"
echo "  2) User-local   → ~/.local/bin/csession      (your user only)"
echo "  3) This project → ./csession                 (this project only)"
echo ""
read -rp "  Choice [1/2/3]: " choice

case "$choice" in
    1)
        INSTALL_PATH="/usr/local/bin/csession"
        info "Installing to $INSTALL_PATH (sudo required)..."
        sudo cp "$CSESSION_SRC" "$INSTALL_PATH"
        sudo chmod +x "$INSTALL_PATH"
        success "Installed to $INSTALL_PATH"
        ;;
    2)
        INSTALL_PATH="$HOME/.local/bin/csession"
        mkdir -p "$HOME/.local/bin"
        cp "$CSESSION_SRC" "$INSTALL_PATH"
        chmod +x "$INSTALL_PATH"
        success "Installed to $INSTALL_PATH"
        # Check PATH
        if [[ ":$PATH:" != *":$HOME/.local/bin:"* ]]; then
            warn "Add ~/.local/bin to your PATH:"
            echo "       echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc && source ~/.bashrc"
        fi
        ;;
    3)
        cp "$CSESSION_SRC" "./csession"
        chmod +x "./csession"
        success "Installed to ./csession (run as: python3 csession <command>)"
        INSTALL_PATH="./csession"
        ;;
    *)
        error "Invalid choice. Run install.sh again."
        ;;
esac

# ── Set up Claude Code hooks for this project ─────────────────────────────────
echo ""
info "Setting up Claude Code hooks in this project..."

if [[ -f ".claude/settings.json" ]]; then
    warn ".claude/settings.json already exists — skipping hook setup to avoid overwriting."
    warn "Manually add the Stop hook. See README.md for instructions."
else
    mkdir -p .claude/hooks
    cp "$SCRIPT_DIR/.claude/hooks/auto_save.py" ".claude/hooks/auto_save.py"
    cp "$SCRIPT_DIR/.claude/settings.json"       ".claude/settings.json"
    success "Claude Code hooks configured at .claude/settings.json"
    success "Stop hook script at .claude/hooks/auto_save.py"
fi

# ── Initialize workspace ──────────────────────────────────────────────────────
echo ""
info "Initializing .claude-session/ workspace..."
if [[ -d ".claude-session" ]]; then
    warn ".claude-session/ already exists — skipping init"
else
    python3 "$CSESSION_SRC" init
fi

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RESET}"
success "Installation complete!"
echo ""
echo -e "${BOLD}Quick start:${RESET}"
echo "  1. Fill in  .claude-session/PROJECT.md    (describe your project)"
echo "  2. Fill in  .claude-session/PROGRESS.md   (add your tasks)"
echo "  3. Run Claude Code on your project"
echo "  4. When done: csession save -m 'what you did'"
echo "  5. Next chat: csession resume --copy  →  paste into Claude"
echo ""
echo -e "${BOLD}The Stop hook will also auto-save whenever Claude Code stops.${RESET}"
echo ""
