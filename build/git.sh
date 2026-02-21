#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/.."

update_directory_structure() {
    find . \
        -not -path './.git/*' \
        -not -path './.venv/*' \
        -not -path '*/__pycache__/*' \
        -not -name '__pycache__' \
        -not -name '*.pyc' \
        | sort > directory_structure.txt
    git add directory_structure.txt
}

case "$1" in
    commit)
        shift
        update_directory_structure
        git add -A
        git commit -m "$*"
        ;;
    *)
        echo "Usage: build/git.sh commit <message>"
        exit 1
        ;;
esac
