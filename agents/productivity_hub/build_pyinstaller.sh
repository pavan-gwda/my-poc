#!/bin/bash

# Build Productivity Hub using PyInstaller

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  Building Productivity Hub macOS App"
echo "========================================"
echo ""

# Use venv from speech_to_text_agent
source ../speech_to_text_agent/venv/bin/activate

# Install PyInstaller if not installed
echo "Installing PyInstaller..."
pip install pyinstaller -q

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist *.spec

# Build the app
echo "Building app..."
pyinstaller \
    --name "Productivity Hub" \
    --windowed \
    --onedir \
    --noconfirm \
    --add-data "config.py:." \
    --add-data "ui:ui" \
    --add-data "core:core" \
    --add-data "modules:modules" \
    --hidden-import "PyQt6" \
    --hidden-import "PyQt6.QtCore" \
    --hidden-import "PyQt6.QtWidgets" \
    --hidden-import "PyQt6.QtGui" \
    --hidden-import "pynput" \
    --hidden-import "pynput.keyboard" \
    --hidden-import "sounddevice" \
    --hidden-import "numpy" \
    --hidden-import "groq" \
    --hidden-import "pyperclip" \
    --hidden-import "watchdog" \
    --hidden-import "watchdog.observers" \
    --hidden-import "watchdog.events" \
    --osx-bundle-identifier "com.productivityhub.app" \
    app.py

echo ""
echo "========================================"
echo "  Build Complete!"
echo "========================================"
echo ""
echo "App location: dist/Productivity Hub.app"
echo ""
echo "To run:"
echo "  open 'dist/Productivity Hub.app'"
echo ""
echo "To share as ZIP:"
echo "  cd dist && zip -r 'ProductivityHub.zip' 'Productivity Hub.app'"
echo ""
