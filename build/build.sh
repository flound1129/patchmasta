#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
VENV_BIN="$([ -d .venv/Scripts ] && echo .venv/Scripts || echo .venv/bin)"
"$VENV_BIN/pip" install -r requirements.txt -r requirements-dev.txt
"$VENV_BIN/pip" install -e . -q
echo "Setup complete. Run with: $VENV_BIN/patchmasta"
