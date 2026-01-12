"""Configuration for Voice Commander."""

CONFIG = {
    # Hotkey to trigger voice command (pynput format)
    # Option key only (alt on Mac)
    "hotkey": {"opt"},

    # Activation mode: "hold" or "toggle"
    "activation_mode": "hold",

    # Use Groq API for better accuracy (requires GROQ_API_KEY)
    "use_groq": True,
    "groq_api_key": "",  # Set via GROQ_API_KEY env variable

    # Local whisper model (if not using Groq)
    "model_size": "base",
    "language": "en",

    # Audio settings
    "sample_rate": 16000,
    "channels": 1,

    # UI settings
    "widget_opacity": 0.95,

    # Confirmation settings
    "confirm_dangerous_actions": True,  # Confirm before shutdown, restart, etc.
    "speak_feedback": False,  # Use TTS for feedback (requires additional setup)
}

# App name aliases (maps spoken names to actual app names)
APP_ALIASES = {
    # Browsers
    "chrome": "Google Chrome",
    "google chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "brave": "Brave Browser",
    "edge": "Microsoft Edge",
    "arc": "Arc",

    # Editors/IDEs
    "sublime": "Sublime Text",
    "sublime text": "Sublime Text",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "visual studio code": "Visual Studio Code",
    "code": "Visual Studio Code",
    "cursor": "Cursor",
    "xcode": "Xcode",
    "android studio": "Android Studio",
    "pycharm": "PyCharm",
    "intellij": "IntelliJ IDEA",
    "vim": "MacVim",
    "neovim": "Neovim",

    # Communication
    "slack": "Slack",
    "teams": "Microsoft Teams",
    "zoom": "zoom.us",
    "discord": "Discord",
    "telegram": "Telegram",
    "whatsapp": "WhatsApp",
    "messages": "Messages",
    "facetime": "FaceTime",

    # Email
    "mail": "Mail",
    "outlook": "Microsoft Outlook",
    "gmail": "Google Chrome",  # Opens in browser

    # Productivity
    "notes": "Notes",
    "reminders": "Reminders",
    "calendar": "Calendar",
    "notion": "Notion",
    "obsidian": "Obsidian",
    "todoist": "Todoist",

    # Media
    "spotify": "Spotify",
    "music": "Music",
    "apple music": "Music",
    "youtube": "YouTube",
    "vlc": "VLC",
    "quicktime": "QuickTime Player",

    # Utilities
    "terminal": "Terminal",
    "iterm": "iTerm",
    "finder": "Finder",
    "activity monitor": "Activity Monitor",
    "system preferences": "System Preferences",
    "settings": "System Preferences",
    "calculator": "Calculator",
    "preview": "Preview",

    # Creative
    "photoshop": "Adobe Photoshop",
    "figma": "Figma",
    "sketch": "Sketch",
    "canva": "Canva",
}

# Website shortcuts
WEBSITE_SHORTCUTS = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "twitter": "https://twitter.com",
    "x": "https://x.com",
    "linkedin": "https://www.linkedin.com",
    "reddit": "https://www.reddit.com",
    "stackoverflow": "https://stackoverflow.com",
    "stack overflow": "https://stackoverflow.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
    "amazon": "https://www.amazon.com",
    "netflix": "https://www.netflix.com",
}
