#!/bin/bash

# Create a DMG for distribution

set -e

cd "$(dirname "$0")"

APP_NAME="Productivity Hub"
DMG_NAME="ProductivityHub-1.0.0"

if [ ! -d "dist/${APP_NAME}.app" ]; then
    echo "Error: App not found. Run ./build.sh first."
    exit 1
fi

echo "Creating DMG..."

# Create a temporary directory for DMG contents
rm -rf dmg_temp
mkdir -p dmg_temp

# Copy app to temp directory
cp -R "dist/${APP_NAME}.app" "dmg_temp/"

# Create symbolic link to Applications folder
ln -s /Applications "dmg_temp/Applications"

# Create the DMG
rm -f "dist/${DMG_NAME}.dmg"
hdiutil create -volname "${APP_NAME}" -srcfolder dmg_temp -ov -format UDZO "dist/${DMG_NAME}.dmg"

# Cleanup
rm -rf dmg_temp

echo ""
echo "DMG created: dist/${DMG_NAME}.dmg"
echo ""
echo "Share this file with others. They can:"
echo "  1. Double-click the DMG"
echo "  2. Drag 'Productivity Hub' to Applications"
echo "  3. Run from Applications folder"
