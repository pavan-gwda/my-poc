#!/bin/bash
# Create DMG installer for Speech-to-Text Agent

set -e

APP_NAME="SpeechToText"
DMG_NAME="SpeechToText-Installer"
VERSION="1.0.0"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if app exists
if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "Error: dist/${APP_NAME}.app not found. Run build.sh first."
    exit 1
fi

echo "Creating DMG installer..."

# Create a temporary directory for DMG contents
DMG_DIR="dist/dmg_temp"
rm -rf "$DMG_DIR"
mkdir -p "$DMG_DIR"

# Copy app to temp directory
cp -R "dist/${APP_NAME}.app" "$DMG_DIR/"

# Create symbolic link to Applications folder
ln -s /Applications "$DMG_DIR/Applications"

# Create DMG
rm -f "dist/${DMG_NAME}.dmg"
hdiutil create -volname "$APP_NAME" \
    -srcfolder "$DMG_DIR" \
    -ov -format UDZO \
    "dist/${DMG_NAME}.dmg"

# Clean up
rm -rf "$DMG_DIR"

echo ""
echo "DMG created: dist/${DMG_NAME}.dmg"
echo ""
echo "To install:"
echo "  1. Double-click the DMG to mount it"
echo "  2. Drag SpeechToText to Applications"
echo "  3. Eject the DMG"
echo "  4. Run SpeechToText from Applications"
