#!/bin/zsh
set -e

TOOLKIT_ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$TOOLKIT_ROOT"

if [ ! -x "$TOOLKIT_ROOT/toolkit/setup_sci_env.command" ]; then
    echo "Sci setup script was not found:"
    echo "$TOOLKIT_ROOT/toolkit/setup_sci_env.command"
    read "?Press Enter to close..."
    exit 1
fi

"$TOOLKIT_ROOT/toolkit/setup_sci_env.command"

echo
echo "Environment is ready."
echo "Run the app with XRD_Finder/run_finder.command or install_macos.command."
read "?Press Enter to close..."
