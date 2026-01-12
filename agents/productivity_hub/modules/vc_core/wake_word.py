"""Wake word detection for Voice Commander."""

import threading
import numpy as np
import sounddevice as sd
from typing import Callable, Optional, List
import time


class WakeWordDetector:
    """Detects wake words using continuous listening and transcription."""

    def __init__(
        self,
        wake_words: List[str],
        transcriber,
        sample_rate: int = 16000,
        chunk_duration: float = 2.0,
        on_wake_word: Optional[Callable] = None,
        enabled: bool = True,
    ):
        """
        Initialize wake word detector.

        Args:
            wake_words: List of wake words/phrases to detect (e.g., ["hey computer", "ok computer"])
            transcriber: Transcriber instance for speech-to-text
            sample_rate: Audio sample rate
            chunk_duration: Duration of each audio chunk to analyze (seconds)
            on_wake_word: Callback when wake word is detected
            enabled: Whether wake word detection is enabled
        """
        self.wake_words = [w.lower().strip() for w in wake_words]
        self.transcriber = transcriber
        self.sample_rate = sample_rate
        self.chunk_duration = chunk_duration
        self.on_wake_word = on_wake_word
        self.enabled = enabled

        self._running = False
        self._thread = None
        self._paused = False
        self._last_detection_time = 0
        self._cooldown = 3.0  # Seconds between detections

    def start(self) -> None:
        """Start wake word detection."""
        if self._running:
            return

        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        print(f"Wake word detection started. Listening for: {self.wake_words}")

    def stop(self) -> None:
        """Stop wake word detection."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=2)
            self._thread = None

    def pause(self) -> None:
        """Temporarily pause detection (e.g., while VC is active)."""
        self._paused = True

    def resume(self) -> None:
        """Resume detection after pause."""
        self._paused = False

    def set_enabled(self, enabled: bool) -> None:
        """Enable or disable wake word detection."""
        self.enabled = enabled
        if not enabled:
            self.stop()
        elif not self._running:
            self.start()

    def set_wake_words(self, wake_words: List[str]) -> None:
        """Update wake words."""
        self.wake_words = [w.lower().strip() for w in wake_words]
        print(f"Wake words updated: {self.wake_words}")

    def _listen_loop(self) -> None:
        """Main listening loop."""
        chunk_samples = int(self.sample_rate * self.chunk_duration)

        while self._running:
            if not self.enabled or self._paused:
                time.sleep(0.1)
                continue

            try:
                # Record audio chunk
                audio = sd.rec(
                    chunk_samples,
                    samplerate=self.sample_rate,
                    channels=1,
                    dtype=np.float32,
                )
                sd.wait()

                if not self._running or self._paused:
                    continue

                # Check if there's enough audio energy (basic VAD)
                audio = audio.flatten()
                if np.abs(audio).max() < 0.01:
                    continue  # Too quiet, skip

                # Check cooldown
                current_time = time.time()
                if current_time - self._last_detection_time < self._cooldown:
                    continue

                # Transcribe and check for wake word
                text = self.transcriber.transcribe(audio, self.sample_rate)
                if text:
                    text_lower = text.lower().strip()
                    for wake_word in self.wake_words:
                        if wake_word in text_lower:
                            print(f"Wake word detected: '{wake_word}' in '{text}'")
                            self._last_detection_time = current_time
                            if self.on_wake_word:
                                self.on_wake_word()
                            break

            except Exception as e:
                print(f"Wake word detection error: {e}")
                time.sleep(0.5)

    def is_running(self) -> bool:
        """Check if wake word detection is running."""
        return self._running and self.enabled
