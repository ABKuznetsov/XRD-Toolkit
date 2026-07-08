#!/bin/zsh
set -e

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
XRD_TOOLKIT_ROOT="$HOME/Library/Application Support/XRD_Toolkit"
XRD_TOOLKIT_ENV="$XRD_TOOLKIT_ROOT/env"
XRD_TOOLKIT_LOGS="$XRD_TOOLKIT_ROOT/logs"
LOG_FILE="$XRD_TOOLKIT_LOGS/setup.log"

mkdir -p "$XRD_TOOLKIT_ROOT" "$XRD_TOOLKIT_LOGS"

echo "[$(date)] Starting XRD_Toolkit setup" > "$LOG_FILE"
echo "Application root: $APP_ROOT" >> "$LOG_FILE"
echo "Toolkit root: $XRD_TOOLKIT_ROOT" >> "$LOG_FILE"

find_python() {
    for candidate in \
        "/opt/homebrew/bin/python3" \
        "/usr/local/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.13/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.12/bin/python3" \
        "/Library/Frameworks/Python.framework/Versions/3.11/bin/python3" \
        "/usr/bin/python3" \
        "python3"
    do
        if command -v "$candidate" >/dev/null 2>&1 && "$candidate" -c "import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)" >/dev/null 2>&1; then
            echo "$candidate"
            return 0
        fi
    done
    return 1
}

install_requirement() {
    local requirement="$1"
    [ -z "$requirement" ] && return 0
    [[ "$requirement" == \#* ]] && return 0
    echo "Installing package: $requirement"
    echo "Installing package: $requirement" >> "$LOG_FILE"
    "$XRD_TOOLKIT_ENV/bin/python" -m pip install --disable-pip-version-check --timeout 60 --retries 3 --prefer-binary --upgrade --upgrade-strategy eager "$requirement" >> "$LOG_FILE" 2>&1
}

PYTHON="$(find_python || true)"
if [ -z "$PYTHON" ]; then
    echo "Python 3.11 or newer was not found."
    echo "Install Python from https://www.python.org/downloads/macos/ or Homebrew, then run this setup again."
    echo "Python 3.11+ not found." >> "$LOG_FILE"
    exit 1
fi

echo "Using Python: $PYTHON"
echo "Using Python: $PYTHON" >> "$LOG_FILE"

if [ ! -x "$XRD_TOOLKIT_ENV/bin/python" ]; then
    echo "Creating XRD_Toolkit environment..."
    echo "Creating venv at $XRD_TOOLKIT_ENV" >> "$LOG_FILE"
    "$PYTHON" -m venv "$XRD_TOOLKIT_ENV" >> "$LOG_FILE" 2>&1
fi

if [ ! -x "$XRD_TOOLKIT_ENV/bin/python" ]; then
    echo "Failed to create XRD_Toolkit environment."
    echo "venv creation failed." >> "$LOG_FILE"
    exit 1
fi

echo "Upgrading pip and build tools..."
echo "Upgrading pip and build tools..." >> "$LOG_FILE"
"$XRD_TOOLKIT_ENV/bin/python" -m pip install --disable-pip-version-check --timeout 60 --retries 3 --prefer-binary --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1

REQ_FILE="$APP_ROOT/XRD_Finder/requirements.txt"
if [ ! -f "$REQ_FILE" ]; then
    echo "Requirements file was not found: $REQ_FILE"
    echo "Requirements file was not found: $REQ_FILE" >> "$LOG_FILE"
    exit 1
fi

echo "Installing XRD Phase Finder requirements..."
echo "Installing XRD Phase Finder requirements..." >> "$LOG_FILE"
while IFS= read -r requirement || [ -n "$requirement" ]; do
    install_requirement "$requirement"
done < "$REQ_FILE"

echo "[$(date)] XRD_Toolkit setup complete." >> "$LOG_FILE"
echo "XRD_Toolkit environment is ready."
