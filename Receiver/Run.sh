#!/bin/bash

set -euo pipefail

HRKLTZ_OPENCTRL_GIT_DIR="/Volumes/Git/GitHub/hrkltz/OpenCtrl"
SCRIPT_DIR="$HRKLTZ_OPENCTRL_GIT_DIR/Receiver"
SCRIPT_VENV_DIR="$SCRIPT_DIR/.venv"

source "$SCRIPT_VENV_DIR/bin/activate"

python3 "$SCRIPT_DIR/main.py" "$@"
