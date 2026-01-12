"""
Setup script for building Productivity Hub as a native macOS app.

Build with:
    python setup.py py2app

The .app will be created in the dist/ folder.
"""

from setuptools import setup
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

APP = ['app.py']
APP_NAME = 'Productivity Hub'

DATA_FILES = [
    ('config', ['config.py']),
]

OPTIONS = {
    'argv_emulation': False,
    'iconfile': None,  # Add icon path here: 'assets/icon.icns'
    'plist': {
        'CFBundleName': APP_NAME,
        'CFBundleDisplayName': APP_NAME,
        'CFBundleIdentifier': 'com.productivityhub.app',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'LSMinimumSystemVersion': '10.15',
        'LSUIElement': True,  # Hide from dock (runs as background/menu bar app)
        'NSMicrophoneUsageDescription': 'Productivity Hub needs microphone access for speech-to-text and voice commands.',
        'NSAppleEventsUsageDescription': 'Productivity Hub needs automation access to control applications.',
        'NSAccessibilityUsageDescription': 'Productivity Hub needs accessibility access for global hotkeys.',
    },
    'packages': [
        'PyQt6',
        'pynput',
        'numpy',
        'sounddevice',
        'groq',
        'pyperclip',
        'watchdog',
        'modules',
        'modules.stt_core',
        'modules.vc_core',
        'modules.burnout_core',
        'modules.burnout_ui',
        'core',
        'ui',
    ],
    'includes': [],
    'excludes': [
        'tkinter',
        'matplotlib',
        'scipy',
        'pandas',
    ],
}

setup(
    name=APP_NAME,
    app=APP,
    data_files=DATA_FILES,
    options={'py2app': OPTIONS},
    setup_requires=['py2app'],
)
