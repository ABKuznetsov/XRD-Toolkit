#!/bin/zsh
set -e

APP_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$APP_ROOT"

echo "Updating XRD Phase Finder from GitHub..."

if [ ! -d ".git" ]; then
    echo "This folder is not a Git checkout."
    echo "Download or clone the repository from https://github.com/ABKuznetsov/XRD_Analysis_Toolkit"
    read "?Press Enter to close..."
    exit 1
fi

if ! command -v git >/dev/null 2>&1; then
    echo "Git was not found."
    echo "Install Git or Xcode Command Line Tools, then run this script again:"
    echo "  xcode-select --install"
    read "?Press Enter to close..."
    exit 1
fi

git fetch origin
git pull --ff-only origin main

echo
echo "Updating Python environment after GitHub update..."
"$APP_ROOT/toolkit/setup_sci_env.command"

echo
echo "Update complete."
read "?Press Enter to close..."
