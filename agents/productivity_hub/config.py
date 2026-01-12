"""Configuration for Productivity Hub - Unified Agent."""
import os
from pathlib import Path

# Load .env.local if it exists
env_local = Path(__file__).parent.parent.parent / ".env.local"
if env_local.exists():
    with open(env_local) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                os.environ.setdefault(key.strip(), value.strip())

CONFIG = {
    # Speech-to-Text settings
    "stt_hotkey": {"caps_lock"},  # Hotkey for speech-to-text (Caps Lock key)
    "stt_activation_mode": "toggle",  # Press to start, press again to stop

    # Voice Commander settings
    "vc_hotkey": {"ctrl_r"},  # Right Control key for voice commands
    "vc_activation_mode": "hold",

    # Burnout Monitor settings
    "work_interval_minutes": 35,
    "short_break_minutes": 5,
    "long_break_minutes": 15,
    "pomodoros_before_long_break": 4,
    "break_extend_minutes": 5,
    "pomodoro_enabled": True,

    # Shared Audio settings
    "sample_rate": 16000,
    "channels": 1,
    "mic_device": None,  # Microphone device ID (None = system default, or use device ID number)

    # Groq API (shared for both STT and Voice Commander)
    "use_groq": True,  # Using Groq cloud API
    "groq_api_key": os.environ.get("GROQ_API_KEY", ""),

    # Local whisper settings (fallback when use_groq is False)
    "model_size": "base",
    "language": "en",

    # UI settings
    "widget_opacity": 0.95,
    "widget_position": "top-right",

    # Voice Commander specific
    "confirm_dangerous_actions": True,
    "speak_feedback": True,  # Enable voice feedback for commands
    "voice_feedback_voice": "Alex",  # macOS voice to use
    "voice_feedback_rate": 200,  # Speech rate (words per minute)

    # Wake word settings
    "wake_word_enabled": False,  # Enable wake word detection
    "wake_words": ["hey computer", "ok computer", "hello computer"],  # Configurable wake words
    "wake_word_cooldown": 3.0,  # Seconds between wake word detections
}

# App name aliases (for voice commander)
APP_ALIASES = {
    "chrome": "Google Chrome",
    "safari": "Safari",
    "firefox": "Firefox",
    "vs code": "Visual Studio Code",
    "vscode": "Visual Studio Code",
    "code": "IntelliJ IDEA",
    "intellij": "IntelliJ IDEA",
    "cursor": "Cursor",
    "sublime": "Sublime Text",
    "terminal": "Terminal",
    "iterm": "iTerm",
    "finder": "Finder",
    "slack": "Slack",
    "spotify": "Spotify",
    "notes": "Notes",
    "mail": "Mail",
    "outlook": "Microsoft Outlook",
    "messages": "Messages",
    "calendar": "Calendar",
    "zoom": "zoom.us",
    "discord": "Discord",
    "postman": "Postman",
}

WEBSITE_SHORTCUTS = {
    "google": "https://www.google.com",
    "youtube": "https://www.youtube.com",
    "github": "https://github.com",
    "gmail": "https://mail.google.com",
    "chatgpt": "https://chat.openai.com",
    "claude": "https://claude.ai",
}

# Messages for burnout monitor alerts
MESSAGES = {
    "break_reminder": [
        "You've been focused for {hours}h {mins}m. Good time for a stretch?",
        "Nice flow! {hours}h {mins}m in. Your brain might like a quick break.",
        "Deep work: {hours}h {mins}m. Coffee? Walk? Just a thought.",
    ],
    "overtime_warning": [
        "Big day - {hours} hours. Wrapping up soon?",
        "You've put in {hours} hours today. Tomorrow will thank you for rest.",
        "{hours} hours logged. You've earned some downtime.",
    ],
    "weekend_warning": [
        "It's the weekend! Just noticed you're working.",
        "Weekend coding detected. Passion project or should you unplug?",
    ],
    "late_night": [
        "It's {time}. Your code will still be here tomorrow.",
        "Late night session. Remember: sleep is a feature, not a bug.",
    ],
    "stuck_detection": [
        "45 min on the same area. Want to step back and rethink?",
        "Noticed you've been here a while. Sometimes a break brings clarity.",
    ],
}
