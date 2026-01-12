"""Configuration for Speech-to-Text Agent."""

CONFIG = {
    # Hotkey configuration (pynput format)
    "hotkey": {"cmd", "shift"},

    # Voice activation: Enable wake word detection ("Hey Jarvis")
    "voice_activation": False,
    "wake_word_threshold": 0.5,  # Detection sensitivity (0.0 to 1.0)

    # Groq API (free tier, uses whisper-large-v3 for better accuracy)
    # Set to True and add your API key from https://console.groq.com/
    "use_groq": True,
    "groq_api_key": "",  # Set via GROQ_API_KEY env variable

    # Whisper model size (for local mode): tiny, base, small, medium, large-v3
    # Smaller = faster but less accurate, larger = slower but more accurate
    "model_size": "base",

    # Language for transcription (None for auto-detect, "en" for English, etc.)
    "language": "en",

    # Output mode: "clipboard", "type", or "both"
    "output_mode": "both",

    # Activation mode: "hold" (press-and-hold) or "toggle" (press to start/stop)
    "activation_mode": "hold",

    # Recording duration for voice activation (seconds)
    "voice_record_duration": 5,

    # Delay between keystrokes when typing (seconds)
    "typing_delay": 0.01,

    # Widget opacity (0.0 to 1.0)
    "widget_opacity": 0.95,

    # Audio settings
    "sample_rate": 16000,  # Whisper expects 16kHz
    "channels": 1,         # Mono audio
}
