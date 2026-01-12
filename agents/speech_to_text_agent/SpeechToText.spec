# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller spec file for Speech-to-Text Agent macOS app."""

import sys
from pathlib import Path

block_cipher = None

# Get the project directory
project_dir = Path(SPECPATH)

a = Analysis(
    ['main.py'],
    pathex=[str(project_dir)],
    binaries=[],
    datas=[
        # Include config file
        ('config.py', '.'),
    ],
    hiddenimports=[
        'PyQt6.QtCore',
        'PyQt6.QtWidgets',
        'PyQt6.QtGui',
        'pynput.keyboard._darwin',
        'pynput.mouse._darwin',
        'faster_whisper',
        'ctranslate2',
        'sounddevice',
        'numpy',
        'pyperclip',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='SpeechToText',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='SpeechToText',
)

app = BUNDLE(
    coll,
    name='SpeechToText.app',
    icon=None,  # Will use default icon, can add custom .icns later
    bundle_identifier='com.speechtotext.agent',
    info_plist={
        'CFBundleName': 'Speech To Text',
        'CFBundleDisplayName': 'Speech To Text',
        'CFBundleVersion': '1.0.0',
        'CFBundleShortVersionString': '1.0.0',
        'NSMicrophoneUsageDescription': 'This app needs microphone access to record your speech for transcription.',
        'NSAppleEventsUsageDescription': 'This app needs accessibility access to type transcribed text.',
        'LSUIElement': True,  # Hide from dock (background app)
        'LSBackgroundOnly': False,
        'NSHighResolutionCapable': True,
    },
)
