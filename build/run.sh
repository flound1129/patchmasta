#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
VENV_BIN="$([ -d .venv/Scripts ] && echo .venv/Scripts || echo .venv/bin)"
"$VENV_BIN/python" main.py
