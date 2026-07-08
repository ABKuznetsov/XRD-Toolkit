#!/bin/zsh
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
VERSION="$("$ROOT"/.venv/bin/python -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])' 2>/dev/null || python3 -c 'import tomllib; print(tomllib.load(open("pyproject.toml", "rb"))["project"]["version"])')"
DMG_NAME="XRD_Phase_Finder_macOS_${VERSION}.dmg"
DIST_DIR="$ROOT/dist"
STAGE_ROOT="$DIST_DIR/macos_dmg"
VOLUME_NAME="XRD Phase Finder ${VERSION}"
PAYLOAD_DIR="$STAGE_ROOT/$VOLUME_NAME"
DMG_PATH="$DIST_DIR/$DMG_NAME"

cd "$ROOT"

if ! command -v hdiutil >/dev/null 2>&1; then
    echo "hdiutil was not found. Build the DMG on macOS."
    exit 1
fi

echo "Building macOS DMG: $DMG_PATH"
rm -rf "$STAGE_ROOT"
mkdir -p "$PAYLOAD_DIR" "$DIST_DIR"

rsync -a \
    --exclude ".git/" \
    --exclude ".DS_Store" \
    --exclude "__MACOSX/" \
    --exclude "__pycache__/" \
    --exclude "*.pyc" \
    --exclude "*.pyo" \
    --exclude ".venv/" \
    --exclude "build/" \
    --exclude "dist/" \
    --exclude "*.egg-info/" \
    --exclude "XRD_Finder/data/" \
    "$ROOT/" "$PAYLOAD_DIR/"

chmod +x "$PAYLOAD_DIR"/install_macos.command "$PAYLOAD_DIR"/update_macos.command "$PAYLOAD_DIR"/toolkit/*.command "$PAYLOAD_DIR"/XRD_Finder/*.command 2>/dev/null || true

cat > "$PAYLOAD_DIR/README_FIRST_macOS.txt" <<README
XRD Phase Finder macOS installer

1. Double-click install_macos.command.
2. The installer creates:
   /Applications/XRD Phase Finder.app when possible,
   otherwise ~/Applications/XRD Phase Finder.app
   ~/Library/Application Support/XRD_Toolkit
3. After installation, launch XRD Phase Finder from Applications,
   Launchpad, Spotlight, or Finder.

If macOS blocks the script, right-click install_macos.command and choose Open,
or run from Terminal:

  xattr -dr com.apple.quarantine .
  ./install_macos.command

Preview launcher:
  toolkit/launch_xrd_finder_preview.command

Manual update:
  update_macos.command
README

rm -f "$DMG_PATH"
hdiutil create \
    -volname "$VOLUME_NAME" \
    -srcfolder "$PAYLOAD_DIR" \
    -ov \
    -format UDZO \
    "$DMG_PATH"

echo "$DMG_PATH"
