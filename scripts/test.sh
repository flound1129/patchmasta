#!/usr/bin/env bash
set -e
.venv/bin/pytest tests/ -v "$@"
