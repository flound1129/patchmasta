#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."
[ -d .venv ] || python3 -m venv .venv
.venv/bin/pip install -r requirements.txt -r requirements-dev.txt
.venv/bin/pip install -e . -q
echo "Setup complete. Run with: .venv/bin/patchmasta"
