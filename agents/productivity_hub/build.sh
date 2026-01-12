#!/bin/bash

# Build Productivity Hub as a native macOS app

set -e

cd "$(dirname "$0")"

echo "========================================"
echo "  Building Productivity Hub macOS App"
echo "========================================"
echo ""

# Use venv from speech_to_text_agent
source ../speech_to_text_agent/venv/bin/activate

# Install py2app if not installed
echo "Installing py2app..."
pip install py2app -q

# Clean previous builds
echo "Cleaning previous builds..."
rm -rf build dist

# Build the app
echo "Building app..."
python setup.py py2app

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
echo "To share:"
echo "  1. Zip the app: cd dist && zip -r 'Productivity Hub.zip' 'Productivity Hub.app'"
echo "  2. Or create DMG (see below)"
echo ""
