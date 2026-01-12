#!/usr/bin/env python3
"""
Speech-to-Text Agent
A floating widget that records speech on hotkey or voice command and transcribes it.
"""

import sys
import threading
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONFIG
from core import AudioRecorder, Transcriber, HotkeyManager, OutputHandler, VoiceActivation
from ui import FloatingWidget


class SpeechToTextAgent(QObject):
    """Main application controller."""

    # Signals for thread-safe UI updates
    status_changed = pyqtSignal(str, str)  # status, message
    transcription_complete = pyqtSignal(str)  # transcribed text
    voice_record_signal = pyqtSignal()  # trigger voice-activated recording
    error_occurred = pyqtSignal(str)  # error message, will auto-reset to idle

    def __init__(self):
        super().__init__()

        # Initialize components
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

        self.output_handler = OutputHandler(
            mode=CONFIG["output_mode"],
            typing_delay=CONFIG["typing_delay"],
        )

        self.hotkey_manager = HotkeyManager(
            hotkey=CONFIG["hotkey"],
            activation_mode=CONFIG["activation_mode"],
            on_activate=self._on_recording_start,
            on_deactivate=self._on_recording_stop,
        )

        # Voice activation (optional)
        self.voice_activation = None
        if CONFIG.get("voice_activation", False):
            self.voice_activation = VoiceActivation(
                on_wake_word=self._on_wake_word_detected,
                threshold=CONFIG.get("wake_word_threshold", 0.5),
                sample_rate=CONFIG["sample_rate"],
            )

        # Create UI
        self.widget = FloatingWidget(
            opacity=CONFIG["widget_opacity"],
            activation_mode=CONFIG["activation_mode"],
        )

        # Connect signals
        self.status_changed.connect(self.widget.set_status)
        self.transcription_complete.connect(self._on_transcription_done)
        self.voice_record_signal.connect(self._start_voice_recording)
        self.error_occurred.connect(self._on_error)
        self.widget.mode_changed.connect(self._on_mode_changed)
        self.widget.quit_requested.connect(self._quit)

        # State
        self._processing = False
        self._voice_recording = False

    def start(self) -> None:
        """Start the agent."""
        print("Speech-to-Text Agent starting...")
        print(f"Hotkey: {CONFIG['hotkey']}")
        print(f"Mode: {CONFIG['activation_mode']}")
        if CONFIG.get("use_groq", False):
            print("Transcription: Groq API (whisper-large-v3)")
        else:
            print(f"Transcription: Local Whisper ({CONFIG['model_size']})")
        if self.voice_activation:
            print("Voice activation: Enabled (say 'Hey Jarvis')")
        print()

        # Load models in background
        self._load_models_async()

        # Start hotkey listener
        self.hotkey_manager.start()

        # Show widget
        self.widget.show()

    def _load_models_async(self) -> None:
        """Load models in a background thread."""
        def load():
            self.status_changed.emit(FloatingWidget.STATUS_PROCESSING, "Loading models...")

            # Load Whisper model
            self.transcriber.load_model()

            # Load wake word model if enabled
            if self.voice_activation:
                self.voice_activation.load_model()
                self.voice_activation.start()

            self.status_changed.emit(FloatingWidget.STATUS_IDLE, "")
            print("Ready! Press hotkey or say 'Hey Jarvis' to start recording.")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    def _on_wake_word_detected(self) -> None:
        """Called when wake word is detected (from background thread)."""
        if self._processing or self._voice_recording:
            return
        # Emit signal to handle in main thread
        self.voice_record_signal.emit()

    def _start_voice_recording(self) -> None:
        """Start voice-activated recording with auto-stop timer."""
        if self._processing or self._voice_recording:
            return

        self._voice_recording = True

        # Pause wake word detection during recording
        if self.voice_activation:
            self.voice_activation.pause()

        # Start recording
        self.status_changed.emit(FloatingWidget.STATUS_RECORDING, "")
        self.audio_recorder.start_recording()
        print("Voice recording started...")

        # Auto-stop after configured duration
        duration_ms = int(CONFIG.get("voice_record_duration", 5) * 1000)
        QTimer.singleShot(duration_ms, self._stop_voice_recording)

    def _stop_voice_recording(self) -> None:
        """Stop voice-activated recording."""
        if not self._voice_recording:
            return

        self._voice_recording = False
        self._on_recording_stop()

        # Resume wake word detection after processing
        QTimer.singleShot(3000, self._resume_voice_activation)

    def _resume_voice_activation(self) -> None:
        """Resume voice activation after processing."""
        if self.voice_activation and not self._processing:
            self.voice_activation.resume()

    def _on_recording_start(self) -> None:
        """Called when recording should start (hotkey)."""
        if self._processing or self._voice_recording:
            return

        # Pause wake word detection during recording
        if self.voice_activation:
            self.voice_activation.pause()

        self.status_changed.emit(FloatingWidget.STATUS_RECORDING, "")
        self.audio_recorder.start_recording()
        print("Recording started...")

    def _on_recording_stop(self) -> None:
        """Called when recording should stop."""
        if not self.audio_recorder.is_recording():
            return

        print("Recording stopped, processing...")
        self._processing = True
        self.status_changed.emit(FloatingWidget.STATUS_PROCESSING, "")

        # Get audio and transcribe in background
        audio = self.audio_recorder.stop_recording()

        def transcribe():
            try:
                if audio.size == 0:
                    self.error_occurred.emit("No audio")
                    self._processing = False
                    return

                text = self.transcriber.transcribe(audio, CONFIG["sample_rate"])

                if text:
                    self.transcription_complete.emit(text)
                else:
                    self.error_occurred.emit("No speech detected")
                    self._processing = False

            except Exception as e:
                print(f"Transcription error: {e}")
                self.error_occurred.emit("Error")
                self._processing = False

        thread = threading.Thread(target=transcribe, daemon=True)
        thread.start()

    def _on_error(self, message: str) -> None:
        """Called when an error occurs, shows error then resets to idle."""
        print(f"Error: {message}")
        self.status_changed.emit(FloatingWidget.STATUS_ERROR, message)

        # Reset to idle after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_changed.emit(
            FloatingWidget.STATUS_IDLE, ""
        ))

        # Resume voice activation if enabled
        self._resume_voice_activation()

    def _on_transcription_done(self, text: str) -> None:
        """Called when transcription is complete."""
        print(f"Transcribed: {text}")

        # Output the text
        self.output_handler.output(text)

        # Show success status briefly
        word_count = len(text.split())
        self.status_changed.emit(
            FloatingWidget.STATUS_DONE,
            f"{word_count} words"
        )

        # Reset to idle after 2 seconds
        QTimer.singleShot(2000, lambda: self.status_changed.emit(
            FloatingWidget.STATUS_IDLE, ""
        ))

        self._processing = False

        # Resume voice activation
        if self.voice_activation:
            QTimer.singleShot(2500, self._resume_voice_activation)

    def _on_mode_changed(self, mode: str) -> None:
        """Called when activation mode is changed via UI."""
        self.hotkey_manager.set_activation_mode(mode)
        print(f"Activation mode changed to: {mode}")

    def _quit(self) -> None:
        """Quit the application."""
        print("Shutting down...")
        self.hotkey_manager.stop()
        if self.voice_activation:
            self.voice_activation.stop()
        QApplication.quit()


def main():
    """Entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    agent = SpeechToTextAgent()
    agent.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
