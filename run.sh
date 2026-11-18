#!/usr/bin/env bash
# ==============================================================================
# SYSCORE Desktop Application Launcher
# ==============================================================================
set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Activate virtual environment if present
if [ -d "$SCRIPT_DIR/.venv" ]; then
    export PATH="$SCRIPT_DIR/.venv/bin:$PATH"
    export LD_LIBRARY_PATH="$SCRIPT_DIR/.venv/lib:${LD_LIBRARY_PATH}"
    export TK_LIBRARY="$SCRIPT_DIR/.venv/lib/tk8.6"
    export TCL_LIBRARY="$SCRIPT_DIR/.venv/lib/tcl8.6"
fi

export MPLCONFIGDIR="/tmp/mplconfig"

# Launch SYSCORE with passed arguments
exec python3 main.py "$@"
