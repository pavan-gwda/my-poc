"""Voice feedback for Voice Commander using macOS text-to-speech."""

import subprocess
import threading
from typing import Optional


class VoiceFeedback:
    """Provides spoken feedback for voice commands."""

    def __init__(self, enabled: bool = True, voice: str = "Samantha", rate: int = 200):
        """
        Initialize voice feedback.

        Args:
            enabled: Whether voice feedback is enabled
            voice: macOS voice to use (Samantha, Alex, Victoria, etc.)
            rate: Speech rate in words per minute (default 200)
        """
        self.enabled = enabled
        self.voice = voice
        self.rate = rate
        self._speaking = False

    def speak(self, text: str, async_speak: bool = True) -> None:
        """
        Speak the given text.

        Args:
            text: Text to speak
            async_speak: If True, speak in background thread
        """
        if not self.enabled or not text:
            return

        if async_speak:
            thread = threading.Thread(target=self._speak_sync, args=(text,), daemon=True)
            thread.start()
        else:
            self._speak_sync(text)

    def _speak_sync(self, text: str) -> None:
        """Speak text synchronously."""
        try:
            self._speaking = True
            subprocess.run(
                ["say", "-v", self.voice, "-r", str(self.rate), text],
                capture_output=True,
                timeout=10
            )
        except Exception:
            pass
        finally:
            self._speaking = False

    def stop(self) -> None:
        """Stop any ongoing speech."""
        try:
            subprocess.run(["killall", "say"], capture_output=True)
        except Exception:
            pass

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable voice feedback."""
        self.enabled = enabled
        if not enabled:
            self.stop()

    def set_voice(self, voice: str) -> None:
        """Set the voice to use."""
        self.voice = voice

    def set_rate(self, rate: int) -> None:
        """Set speech rate (words per minute)."""
        self.rate = max(100, min(400, rate))


# Response templates for different command types
FEEDBACK_TEMPLATES = {
    # App commands
    "open_app": [
        "Opening {app_name}",
        "Launching {app_name}",
    ],
    "close_app": [
        "Closing {app_name}",
        "Quitting {app_name}",
    ],
    "switch_app": [
        "Switching to {app_name}",
    ],
    "minimize_app": [
        "Minimizing {app_name}",
        "Hiding {app_name}",
    ],

    # Volume commands
    "volume_up": ["Volume up"],
    "volume_down": ["Volume down"],
    "volume_mute": ["Toggling mute"],
    "volume_set": ["Setting volume to {level} percent"],

    # Brightness
    "brightness_up": ["Brightness up"],
    "brightness_down": ["Brightness down"],

    # Screenshot
    "screenshot": ["Taking screenshot"],
    "screenshot_area": ["Select the area to capture"],

    # System
    "sleep": ["Going to sleep"],
    "lock": ["Locking screen"],

    # Media
    "play_pause": ["Toggling playback"],
    "next_track": ["Next track"],
    "prev_track": ["Previous track"],

    # Web
    "search_web": ["Searching for {query}"],
    "open_url": ["Opening the website"],
    "open_website": ["Opening {website}"],

    # Unknown
    "unknown": ["Sorry, I didn't understand that"],
}

# Success/failure responses
SUCCESS_RESPONSES = [
    "Done",
    "Got it",
    "Sure",
    "Okay",
]

FAILURE_RESPONSES = [
    "Sorry, couldn't do that",
    "That didn't work",
    "Something went wrong",
]


def get_feedback_text(command_type: str, params: dict, success: bool = True) -> str:
    """
    Get appropriate feedback text for a command.

    Args:
        command_type: The type of command executed
        params: Command parameters
        success: Whether the command succeeded

    Returns:
        Feedback text to speak
    """
    import random

    if not success:
        return random.choice(FAILURE_RESPONSES)

    templates = FEEDBACK_TEMPLATES.get(command_type, ["Command executed"])
    template = random.choice(templates)

    # Format with params
    try:
        return template.format(**params)
    except KeyError:
        return template
