"""Audio recording module using sounddevice."""

import numpy as np
import sounddevice as sd
from typing import Optional
import threading
import io
import wave


class AudioRecorder:
    """Records audio from the microphone."""

    def __init__(self, sample_rate: int = 16000, channels: int = 1, device: Optional[int] = None):
        self.sample_rate = sample_rate
        self.channels = channels
        self.device = device  # None = system default
        self.recording = False
        self.audio_data: list[np.ndarray] = []
        self._lock = threading.Lock()
        self._stream: Optional[sd.InputStream] = None

    @staticmethod
    def list_devices() -> list[dict]:
        """List available audio input devices."""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:  # Input devices only
                devices.append({
                    'id': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                    'default': dev == sd.query_devices(kind='input')
                })
        return devices

    def start_recording(self) -> None:
        """Start recording audio from the microphone."""
        import time
        with self._lock:
            if self.recording:
                print("[AudioRecorder] Already recording, ignoring start")
                return

            self.audio_data = []
            self.recording = True
            self._start_time = time.time()

            try:
                self._stream = sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    dtype=np.float32,
                    device=self.device,
                    callback=self._audio_callback,
                )
                self._stream.start()
                device_name = sd.query_devices(self.device or sd.default.device[0])['name'] if self.device is not None or sd.default.device[0] is not None else 'default'
                print(f"[AudioRecorder] Started recording on '{device_name}' (stream active: {self._stream.active})")
            except Exception as e:
                print(f"[AudioRecorder] Failed to start: {e}")
                self.recording = False
                raise

    def stop_recording(self) -> np.ndarray:
        """Stop recording and return the audio data as a numpy array."""
        import time
        with self._lock:
            if not self.recording:
                print("[AudioRecorder] Not recording, returning empty")
                return np.array([], dtype=np.float32)

            self.recording = False
            duration = time.time() - getattr(self, '_start_time', time.time())

            if self._stream:
                try:
                    self._stream.stop()
                    self._stream.close()
                except Exception as e:
                    print(f"[AudioRecorder] Error stopping stream: {e}")
                self._stream = None

            if not self.audio_data:
                print(f"[AudioRecorder] Stopped after {duration:.1f}s - no audio data!")
                return np.array([], dtype=np.float32)

            # Concatenate all recorded chunks
            audio = np.concatenate(self.audio_data, axis=0)
            chunk_count = len(self.audio_data)
            self.audio_data = []

            # Flatten to 1D if mono
            if self.channels == 1:
                audio = audio.flatten()

            audio_duration = len(audio) / self.sample_rate
            print(f"[AudioRecorder] Stopped after {duration:.1f}s - captured {audio_duration:.1f}s audio ({chunk_count} chunks)")

            return audio

    def _audio_callback(
        self, indata: np.ndarray, frames: int, time_info, status
    ) -> None:
        """Callback function for the audio stream."""
        if status:
            print(f"Audio callback status: {status}")
        if self.recording:
            self.audio_data.append(indata.copy())

    def is_recording(self) -> bool:
        """Check if currently recording."""
        return self.recording

    def get_audio_as_wav_bytes(self, audio: np.ndarray) -> bytes:
        """Convert numpy audio array to WAV bytes for compatibility."""
        # Convert float32 [-1, 1] to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write to WAV in memory
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        buffer.seek(0)
        return buffer.read()
