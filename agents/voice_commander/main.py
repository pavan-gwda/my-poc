#!/usr/bin/env python3
"""
Voice Commander
A voice-controlled assistant that executes system commands.
"""

import sys
import os
import threading

# Add parent directory to path to import from speech_to_text_agent
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONFIG, APP_ALIASES, WEBSITE_SHORTCUTS
from core import CommandParser, ActionExecutor
from ui import FloatingWidget

# Import from speech_to_text_agent
from speech_to_text_agent.core import AudioRecorder, Transcriber, HotkeyManager


class VoiceCommander(QObject):
    """Main application controller."""

    # Signals for thread-safe UI updates
    status_changed = pyqtSignal(str, str, str)  # status, message, command
    command_executed = pyqtSignal(bool, str)  # success, message

    def __init__(self):
        super().__init__()

        # Initialize audio components
        self.audio_recorder = AudioRecorder(
            sample_rate=CONFIG["sample_rate"],
            channels=CONFIG["channels"],
        )

        self.transcriber = Transcriber(
            model_size=CONFIG["model_size"],
            language=CONFIG["language"],
            use_groq=CONFIG.get("use_groq", False),
            groq_api_key=CONFIG.get("groq_api_key"),
        )

        # Command processing
        self.command_parser = CommandParser(APP_ALIASES, WEBSITE_SHORTCUTS)
        self.action_executor = ActionExecutor()

        # Hotkey manager
        self.hotkey_manager = HotkeyManager(
            hotkey=CONFIG["hotkey"],
            activation_mode=CONFIG["activation_mode"],
            on_activate=self._on_recording_start,
            on_deactivate=self._on_recording_stop,
        )

        # UI
        self.widget = FloatingWidget(
            opacity=CONFIG["widget_opacity"],
            activation_mode=CONFIG["activation_mode"],
        )

        # Connect signals
        self.status_changed.connect(self.widget.set_status)
        self.command_executed.connect(self._on_command_executed)
        self.widget.mode_changed.connect(self._on_mode_changed)
        self.widget.quit_requested.connect(self._quit)

        # State
        self._processing = False

    def start(self) -> None:
        """Start the voice commander."""
        print("Voice Commander starting...")
        print(f"Hotkey: {CONFIG['hotkey']}")
        print(f"Mode: {CONFIG['activation_mode']}")
        if CONFIG.get("use_groq", False):
            print("Transcription: Groq API (whisper-large-v3)")
        else:
            print(f"Transcription: Local Whisper ({CONFIG['model_size']})")
        print()
        print("Supported commands:")
        print("  - 'Open <app>' / 'Close <app>'")
        print("  - 'Volume up/down/mute'")
        print("  - 'Screenshot' / 'Screenshot area'")
        print("  - 'Search <query>'")
        print("  - 'Go to <website>'")
        print("  - 'Lock' / 'Sleep'")
        print()

        # Load models in background
        self._load_models_async()

        # Start hotkey listener
        self.hotkey_manager.start()

        # Show widget
        self.widget.show()

    def _load_models_async(self) -> None:
        """Load models in background thread."""
        def load():
            self.status_changed.emit(FloatingWidget.STATUS_PROCESSING, "Loading...", "")
            self.transcriber.load_model()
            self.status_changed.emit(FloatingWidget.STATUS_IDLE, "", "")
            print("Ready! Hold hotkey and speak a command.")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _on_recording_start(self) -> None:
        """Called when recording should start."""
        if self._processing:
            return

        self.status_changed.emit(FloatingWidget.STATUS_LISTENING, "", "")
        self.audio_recorder.start_recording()
        print("Listening...")

    def _on_recording_stop(self) -> None:
        """Called when recording should stop."""
        if not self.audio_recorder.is_recording():
            return

        print("Processing...")
        self._processing = True
        self.status_changed.emit(FloatingWidget.STATUS_PROCESSING, "", "")

        # Get audio and process in background
        audio = self.audio_recorder.stop_recording()

        def process():
            try:
                if audio.size == 0:
                    self.status_changed.emit(FloatingWidget.STATUS_ERROR, "No audio", "")
                    self._processing = False
                    return

                # Transcribe
                text = self.transcriber.transcribe(audio, CONFIG["sample_rate"])

                if not text:
                    self.status_changed.emit(FloatingWidget.STATUS_ERROR, "No speech", "")
                    self._processing = False
                    return

                print(f"Heard: '{text}'")

                # Parse command
                command = self.command_parser.parse(text)
                print(f"Parsed: {command.command_type.value} - {command.params}")

                # Show what we're executing
                self.status_changed.emit(
                    FloatingWidget.STATUS_EXECUTING,
                    f"{command.command_type.value.replace('_', ' ').title()}",
                    text
                )

                # Execute command
                success, message = self.action_executor.execute(command)
                print(f"Result: {success} - {message}")

                self.command_executed.emit(success, message)

            except Exception as e:
                print(f"Error: {e}")
                self.status_changed.emit(FloatingWidget.STATUS_ERROR, "Error", "")
                self._processing = False

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _on_command_executed(self, success: bool, message: str) -> None:
        """Called when command execution is complete."""
        if success:
            self.status_changed.emit(FloatingWidget.STATUS_SUCCESS, message, "")
        else:
            self.status_changed.emit(FloatingWidget.STATUS_ERROR, message, "")

        # Reset to idle after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_changed.emit(
            FloatingWidget.STATUS_IDLE, "", ""
        ))

        self._processing = False

    def _on_mode_changed(self, mode: str) -> None:
        """Called when activation mode is changed."""
        self.hotkey_manager.set_activation_mode(mode)
        print(f"Activation mode changed to: {mode}")

    def _quit(self) -> None:
        """Quit the application."""
        print("Shutting down...")
        self.hotkey_manager.stop()
        QApplication.quit()


def main():
    """Entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    commander = VoiceCommander()
    commander.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
