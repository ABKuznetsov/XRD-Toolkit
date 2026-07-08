#!/bin/zsh
set -e
unsetopt BG_NICE 2>/dev/null || true

APP_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
XRD_TOOLKIT_ROOT="$HOME/Library/Application Support/XRD_Toolkit"
XRD_TOOLKIT_ENV="$XRD_TOOLKIT_ROOT/env"
XRD_FINDER_USER_ROOT="$XRD_TOOLKIT_ROOT/XRD_Finder"
XRD_TOOLKIT_LOGS="$XRD_TOOLKIT_ROOT/logs"
LOG_FILE="$XRD_TOOLKIT_LOGS/xrd_finder_console.log"
READY_FILE="$XRD_TOOLKIT_ROOT/xrd_finder_ready"

mkdir -p "$XRD_TOOLKIT_ROOT" "$XRD_FINDER_USER_ROOT" "$XRD_TOOLKIT_LOGS"

echo "XRD Phase Finder startup preview"
echo "Application root: $APP_ROOT"
echo "Log file: $LOG_FILE"
echo

if [ ! -x "$XRD_TOOLKIT_ENV/bin/python" ]; then
    echo "1/4 Installing scientific Python environment..."
    "$APP_ROOT/toolkit/setup_xrd_toolkit_env.command"
else
    echo "1/4 Environment ready."
fi

if [ -d "$APP_ROOT/.git" ] && command -v git >/dev/null 2>&1; then
    echo "2/4 Checking GitHub updates..."
    (
        cd "$APP_ROOT"
        git fetch origin >/dev/null 2>&1 || exit 0
        LOCAL_REV="$(git rev-parse @ 2>/dev/null || true)"
        UPSTREAM_REV="$(git rev-parse @{u} 2>/dev/null || git rev-parse origin/main 2>/dev/null || true)"
        BASE_REV="$(git merge-base @ "$UPSTREAM_REV" 2>/dev/null || true)"
        if [ -n "$LOCAL_REV" ] && [ -n "$UPSTREAM_REV" ] && [ "$LOCAL_REV" != "$UPSTREAM_REV" ] && [ "$LOCAL_REV" = "$BASE_REV" ]; then
            echo "   Updating source..."
            git pull --ff-only >/dev/null
            "$APP_ROOT/toolkit/setup_xrd_toolkit_env.command"
        else
            echo "   Already up to date."
        fi
    ) || echo "   Auto-update skipped. Use update_macos.command for details."
else
    echo "2/4 Auto-update skipped: this is not a Git checkout or git is unavailable."
fi

echo "3/4 Starting XRD Phase Finder..."
export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="$APP_ROOT/XRD_Finder${PYTHONPATH+:$PYTHONPATH}"
export XRD_FINDER_DATA_DIR="$XRD_FINDER_USER_ROOT/data"
export MPLCONFIGDIR="$XRD_FINDER_USER_ROOT/matplotlib"
export XRD_FINDER_READY_FILE="$READY_FILE"
export QT_MAC_WANTS_LAYER=1
rm -f "$READY_FILE"
echo "[$(date)] Starting XRD Phase Finder" > "$LOG_FILE"

"$XRD_TOOLKIT_ENV/bin/python" -m xrd_finder.apps.finder_gui "$@" >> "$LOG_FILE" 2>&1 &
APP_PID="$!"

echo "4/4 Waiting for application window..."
for _ in {1..120}; do
    if [ -f "$READY_FILE" ]; then
        echo "XRD Phase Finder is running."
        exit 0
    fi
    if ! kill -0 "$APP_PID" >/dev/null 2>&1; then
        echo
        echo "XRD Phase Finder exited during startup."
        echo "Last log lines:"
        tail -30 "$LOG_FILE" 2>/dev/null || true
        read "?Press Enter to close..."
        exit 1
    fi
    sleep 1
done

echo "Startup is taking longer than expected. The app may still be opening."
echo "Last log lines:"
tail -20 "$LOG_FILE" 2>/dev/null || true
read "?Press Enter to close..."
