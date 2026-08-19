#!/usr/bin/env bash
# nes-wrapper.sh — symlinked to ~/.local/bin/nes.
# Activates the managed venv and execs the real nes CLI.

OPENJARVIS_HOME="${OPENJARVIS_HOME:-$HOME/.nes}"
VENV="$OPENJARVIS_HOME/.venv"

if [[ ! -d "$VENV" ]]; then
    echo "nes: venv not found at $VENV" >&2
    echo "Re-run the installer: curl -fsSL https://open-nes.github.io/NES/install.sh | bash" >&2
    exit 1
fi

exec "$VENV/bin/nes" "$@"
