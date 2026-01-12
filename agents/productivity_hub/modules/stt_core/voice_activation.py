"""Voice activation using wake word detection."""

import numpy as np
import sounddevice as sd
import threading
from typing import Callable, Optional
from openwakeword.model import Model


class VoiceActivation:
    """Detects wake words to trigger recording."""

    def __init__(
        self,
        on_wake_word: Optional[Callable[[], None]] = None,
        threshold: float = 0.5,
        sample_rate: int = 16000,
    ):
        """
        Initialize voice activation.

        Args:
            on_wake_word: Callback when wake word is detected
            threshold: Detection threshold (0.0 to 1.0)
            sample_rate: Audio sample rate
        """
        self.on_wake_word = on_wake_word
        self.threshold = threshold
        self.sample_rate = sample_rate

        self._model: Optional[Model] = None
        self._running = False
        self._paused = False
        self._thread: Optional[threading.Thread] = None
        self._stream: Optional[sd.InputStream] = None
        self._lock = threading.Lock()

    def load_model(self) -> None:
        """Load the wake word model."""
        if self._model is None:
            print("Loading wake word model...")
            # Only load "hey jarvis" model for efficiency
            self._model = Model(
                wakeword_models=["hey_jarvis_v0.1"],
                inference_framework='onnx'
            )
            print("Say 'Hey Jarvis' to start recording!")

    def start(self) -> None:
        """Start listening for wake words."""
        if self._running:
            return

        if self._model is None:
            self.load_model()

        self._running = True
        self._paused = False
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop listening for wake words."""
        self._running = False
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None

    def pause(self) -> None:
        """Pause wake word detection (during recording/processing)."""
        self._paused = True

    def resume(self) -> None:
        """Resume wake word detection."""
        self._paused = False

    def _listen_loop(self) -> None:
        """Main listening loop."""
        chunk_size = 1280  # ~80ms at 16kHz

        def audio_callback(indata, frames, time_info, status):
            if self._paused or not self._running:
                return

            # Convert to int16 for openwakeword
            audio_int16 = (indata.flatten() * 32767).astype(np.int16)

            # Run prediction
            prediction = self._model.predict(audio_int16)

            # Check all wake word models
            for model_name, score in prediction.items():
                if score > self.threshold:
                    print(f"Wake word detected: {model_name} (score: {score:.2f})")
                    if self.on_wake_word:
                        self.on_wake_word()
                    # Reset the model to avoid repeated triggers
                    self._model.reset()
                    break

        try:
            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=1,
                dtype=np.float32,
                blocksize=chunk_size,
                callback=audio_callback,
            )
            self._stream.start()

            # Keep thread alive
            while self._running:
                sd.sleep(100)

        except Exception as e:
            print(f"Voice activation error: {e}")
        finally:
            if self._stream:
                self._stream.stop()
                self._stream.close()
                self._stream = None
