"""Speech-to-text transcription using Groq API, local Whisper, or Distil-Whisper."""

import os
import io
import wave
import tempfile
import numpy as np
from typing import Optional


class Transcriber:
    """Transcribes audio using Groq API, local faster-whisper, or distil-whisper."""

    def __init__(
        self,
        model_size: str = "base",
        device: str = "auto",
        compute_type: str = "auto",
        language: Optional[str] = "en",
        use_groq: bool = False,
        groq_api_key: Optional[str] = None,
        use_distil: bool = False,
    ):
        self.model_size = model_size
        self.language = language
        self.use_groq = use_groq
        self.use_distil = use_distil
        self._device = device
        self._compute_type = compute_type

        # Groq setup
        self._groq_client = None
        self._groq_api_key = groq_api_key or os.environ.get("GROQ_API_KEY")

        # Local whisper setup
        self._local_model = None

        # Distil-whisper setup
        self._distil_model = None
        self._distil_processor = None

    def load_model(self) -> None:
        """Load the transcription model."""
        if self.use_groq:
            self._setup_groq()
        elif self.use_distil:
            self._setup_distil_whisper()
        else:
            self._setup_local_whisper()

    def _setup_groq(self) -> None:
        """Set up Groq client."""
        if self._groq_client is None:
            from groq import Groq
            print("Setting up Groq Whisper API...")
            self._groq_client = Groq(api_key=self._groq_api_key)
            print("Groq API ready! (Using whisper-large-v3)")

    def _setup_local_whisper(self) -> None:
        """Set up local faster-whisper."""
        if self._local_model is None:
            from faster_whisper import WhisperModel
            print(f"Loading local Whisper model: {self.model_size}...")
            self._local_model = WhisperModel(
                self.model_size,
                device=self._device,
                compute_type=self._compute_type,
            )
            print("Model loaded successfully.")

    def _setup_distil_whisper(self) -> None:
        """Set up distil-whisper using transformers."""
        if self._distil_model is None:
            import torch
            from transformers import AutoModelForSpeechSeq2Seq, AutoProcessor, pipeline

            print("Loading Distil-Whisper model (this may take a moment)...")

            # Determine device
            if torch.cuda.is_available():
                device = "cuda:0"
                torch_dtype = torch.float16
            elif torch.backends.mps.is_available():
                device = "mps"
                torch_dtype = torch.float16
            else:
                device = "cpu"
                torch_dtype = torch.float32

            model_id = "distil-whisper/distil-large-v3"

            self._distil_model = AutoModelForSpeechSeq2Seq.from_pretrained(
                model_id,
                torch_dtype=torch_dtype,
                low_cpu_mem_usage=True,
                use_safetensors=True,
            )
            self._distil_model.to(device)

            self._distil_processor = AutoProcessor.from_pretrained(model_id)

            self._distil_pipe = pipeline(
                "automatic-speech-recognition",
                model=self._distil_model,
                tokenizer=self._distil_processor.tokenizer,
                feature_extractor=self._distil_processor.feature_extractor,
                torch_dtype=torch_dtype,
                device=device,
            )

            print(f"Distil-Whisper loaded on {device}!")

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """Transcribe audio to text."""
        if audio.size == 0:
            return ""

        if self.use_groq:
            return self._transcribe_groq(audio, sample_rate)
        elif self.use_distil:
            return self._transcribe_distil(audio, sample_rate)
        else:
            return self._transcribe_local(audio, sample_rate)

    def _transcribe_groq(self, audio: np.ndarray, sample_rate: int) -> str:
        """Transcribe using Groq API."""
        import time
        start_time = time.time()

        if self._groq_client is None:
            self._setup_groq()

        # Convert numpy array to WAV bytes
        wav_bytes = self._audio_to_wav_bytes(audio, sample_rate)
        audio_duration = len(audio) / sample_rate

        # Create a temporary file (Groq requires file-like object)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(wav_bytes)
            temp_path = f.name

        try:
            print(f"[Transcriber] Sending {audio_duration:.1f}s audio to Groq API...")
            with open(temp_path, "rb") as audio_file:
                transcription = self._groq_client.audio.transcriptions.create(
                    file=("audio.wav", audio_file.read()),
                    model="whisper-large-v3",
                    language=self.language,
                )
            elapsed = time.time() - start_time
            print(f"[Transcriber] Groq API response in {elapsed:.2f}s")
            return transcription.text.strip()
        except Exception as e:
            elapsed = time.time() - start_time
            print(f"[Transcriber] Groq API error after {elapsed:.2f}s: {e}")
            raise
        finally:
            try:
                os.unlink(temp_path)
            except Exception:
                pass

    def _transcribe_distil(self, audio: np.ndarray, sample_rate: int) -> str:
        """Transcribe using distil-whisper."""
        if self._distil_model is None:
            self._setup_distil_whisper()

        # Ensure audio is float32 and normalized
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        # Use the pipeline
        result = self._distil_pipe(
            {"raw": audio, "sampling_rate": sample_rate},
            return_timestamps=False,
        )

        return result["text"].strip()

    def _transcribe_local(self, audio: np.ndarray, sample_rate: int) -> str:
        """Transcribe using local faster-whisper."""
        if self._local_model is None:
            self._setup_local_whisper()

        # Ensure audio is float32 and normalized
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if np.abs(audio).max() > 1.0:
            audio = audio / np.abs(audio).max()

        segments, info = self._local_model.transcribe(
            audio,
            language=self.language,
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(min_silence_duration_ms=500),
        )

        text_parts = []
        for segment in segments:
            text_parts.append(segment.text.strip())

        return " ".join(text_parts).strip()

    def _audio_to_wav_bytes(self, audio: np.ndarray, sample_rate: int) -> bytes:
        """Convert numpy audio array to WAV bytes."""
        # Ensure float32
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        # Normalize
        if np.abs(audio).max() > 0:
            audio = audio / np.abs(audio).max()

        # Convert to int16
        audio_int16 = (audio * 32767).astype(np.int16)

        # Write to WAV buffer
        buffer = io.BytesIO()
        with wave.open(buffer, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio_int16.tobytes())

        buffer.seek(0)
        return buffer.read()

    def is_loaded(self) -> bool:
        """Check if the model is loaded."""
        if self.use_groq:
            return self._groq_client is not None
        elif self.use_distil:
            return self._distil_model is not None
        return self._local_model is not None
