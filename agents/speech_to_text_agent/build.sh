#!/bin/bash
# Build script for Speech-to-Text Agent macOS app

set -e

echo "========================================"
echo "  Speech-to-Text Agent - Build Script"
echo "========================================"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo -e "${YELLOW}Creating virtual environment...${NC}"
    python3 -m venv venv
fi

# Activate virtual environment
echo -e "${YELLOW}Activating virtual environment...${NC}"
source venv/bin/activate

# Install dependencies
echo -e "${YELLOW}Installing dependencies...${NC}"
pip install --upgrade pip
pip install -r requirements.txt

# Clean previous builds
echo -e "${YELLOW}Cleaning previous builds...${NC}"
rm -rf build dist

# Build the app
echo -e "${YELLOW}Building macOS app bundle...${NC}"
pyinstaller SpeechToText.spec --noconfirm

# Check if build succeeded
if [ -d "dist/SpeechToText.app" ]; then
    echo
    echo -e "${GREEN}========================================"
    echo "  Build successful!"
    echo "========================================"
    echo -e "${NC}"
    echo "App location: dist/SpeechToText.app"
    echo
    echo "To install:"
    echo "  1. Drag 'dist/SpeechToText.app' to your Applications folder"
    echo "  2. Double-click to run"
    echo "  3. Grant permissions when prompted:"
    echo "     - Microphone access"
    echo "     - Accessibility (System Settings > Privacy & Security > Accessibility)"
    echo "     - Input Monitoring (System Settings > Privacy & Security > Input Monitoring)"
    echo
    echo "To start automatically on login:"
    echo "  System Settings > General > Login Items > Add SpeechToText"
    echo

    # Ask if user wants to open the dist folder
    read -p "Open dist folder in Finder? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        open dist
    fi
else
    echo -e "${RED}Build failed!${NC}"
    exit 1
fi
