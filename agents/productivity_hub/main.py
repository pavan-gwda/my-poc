#!/usr/bin/env python3
"""
Productivity Hub - Unified Agent
Combines Speech-to-Text, Voice Commander, and Burnout Monitor in one application.
"""

import sys
import os
import threading
import logging
from pathlib import Path
from datetime import datetime

# Add parent directory to path to import from other agents
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Setup logging
LOG_DIR = Path(__file__).parent / "logs"
LOG_DIR.mkdir(exist_ok=True)
LOG_FILE = LOG_DIR / f"productivity_hub_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)  # Also print to stdout if running in foreground
    ]
)
logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONFIG, APP_ALIASES, WEBSITE_SHORTCUTS
from ui.unified_widget import UnifiedWidget

# Import from speech_to_text_agent
from speech_to_text_agent.core import AudioRecorder, Transcriber, OutputHandler

# Import combined hotkey manager and command logger
from core import CombinedHotkeyManager, CommandLogger

# Import from voice_commander
from voice_commander.core import CommandParser, ActionExecutor, VoiceFeedback, get_feedback_text, WakeWordDetector

# Import from burnout_monitor
from burnout_monitor.core import DataStore, ActivityMonitor, AnalysisEngine, PomodoroTimer
from burnout_monitor.ui import StatsDialog, BreakPopup, BreakTimerPopup, SettingsDialog
from burnout_monitor.ui.break_popup import SoundPlayer


class ProductivityHub(QObject):
    """Main unified controller combining all agents."""

    # STT signals
    stt_status_changed = pyqtSignal(str, str)
    stt_transcription_complete = pyqtSignal(str)

    # VC signals
    vc_status_changed = pyqtSignal(str, str)
    vc_command_executed = pyqtSignal(bool, str)

    # Burnout signals
    burnout_status_update = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        # Load burnout settings
        self.settings = SettingsDialog.load_settings()

        # ===== Speech-to-Text Components =====
        self.stt_audio_recorder = AudioRecorder(
            sample_rate=CONFIG["sample_rate"],
            channels=CONFIG["channels"],
            device=self.settings.get("mic_device"),
        )

        self.stt_transcriber = Transcriber(
            model_size=CONFIG["model_size"],
            language=CONFIG["language"],
            use_groq=CONFIG.get("use_groq", True),
            groq_api_key=CONFIG.get("groq_api_key"),
        )

        self.output_handler = OutputHandler(
            mode="type",  # Only type at cursor, no clipboard
            typing_delay=0.01,
        )

        # ===== Voice Commander Components =====
        self.vc_audio_recorder = AudioRecorder(
            sample_rate=CONFIG["sample_rate"],
            channels=CONFIG["channels"],
            device=self.settings.get("mic_device"),
        )

        self.vc_transcriber = Transcriber(
            model_size=CONFIG["model_size"],
            language=CONFIG["language"],
            use_groq=CONFIG.get("use_groq", True),
            groq_api_key=CONFIG.get("groq_api_key"),
        )

        self.command_parser = CommandParser(APP_ALIASES, WEBSITE_SHORTCUTS)
        self.action_executor = ActionExecutor()

        # Command logger for audit trail
        self.command_logger = CommandLogger()

        # Voice feedback for spoken responses
        self.voice_feedback = VoiceFeedback(
            enabled=CONFIG.get("speak_feedback", True),
            voice=CONFIG.get("voice_feedback_voice", "Samantha"),
            rate=CONFIG.get("voice_feedback_rate", 200)
        )

        # Wake word detector for hands-free activation
        self.wake_word_detector = WakeWordDetector(
            wake_words=CONFIG.get("wake_words", ["hey computer"]),
            transcriber=self.vc_transcriber,
            sample_rate=CONFIG["sample_rate"],
            chunk_duration=2.0,
            on_wake_word=self._on_wake_word_detected,
            enabled=CONFIG.get("wake_word_enabled", False),
        )

        # ===== Combined Hotkey Manager =====
        self.hotkey_manager = CombinedHotkeyManager()
        self.hotkey_manager.add_hotkey(
            name="stt",
            hotkey=self.settings.get("stt_hotkey", CONFIG["stt_hotkey"]),
            activation_mode=self.settings.get("stt_activation_mode", CONFIG["stt_activation_mode"]),
            on_activate=self._on_stt_recording_start,
            on_deactivate=self._on_stt_recording_stop,
        )
        self.hotkey_manager.add_hotkey(
            name="vc",
            hotkey=self.settings.get("vc_hotkey", CONFIG["vc_hotkey"]),
            activation_mode=self.settings.get("vc_activation_mode", CONFIG["vc_activation_mode"]),
            on_activate=self._on_vc_recording_start,
            on_deactivate=self._on_vc_recording_stop,
        )

        # ===== Burnout Monitor Components =====
        self.data_store = DataStore()
        self.analysis = AnalysisEngine(self.data_store, self.settings)

        watch_dirs = self.settings.get("watch_directories") or [str(Path.home() / "projects")]
        self.activity_monitor = ActivityMonitor(
            on_activity=self._on_activity,
            watch_directories=watch_dirs,
            exclude_directories=set(self.settings.get("exclude_directories", [])),
        )

        self.pomodoro = None
        if CONFIG.get("pomodoro_enabled", True):
            self.pomodoro = PomodoroTimer(
                work_minutes=CONFIG.get("work_interval_minutes", 25),
                short_break_minutes=CONFIG.get("short_break_minutes", 5),
                long_break_minutes=CONFIG.get("long_break_minutes", 15),
                pomodoros_until_long_break=CONFIG.get("pomodoros_before_long_break", 4),
                data_store=self.data_store,
            )
            self.pomodoro.tick.connect(self._on_pomodoro_tick)
            self.pomodoro.break_time.connect(self._on_pomodoro_break)
            self.pomodoro.work_session_complete.connect(self._on_work_complete)

        # ===== Unified UI =====
        self.widget = UnifiedWidget(
            opacity=CONFIG["widget_opacity"],
            position=CONFIG["widget_position"],
        )

        # Break timer popup
        self.break_timer_popup = None

        # Connect STT signals
        self.stt_status_changed.connect(self.widget.set_stt_status)
        self.stt_transcription_complete.connect(self._on_stt_transcription_done)

        # Connect VC signals
        self.vc_status_changed.connect(self.widget.set_vc_status)
        self.vc_command_executed.connect(self._on_vc_command_executed)

        # Connect Burnout signals
        self.burnout_status_update.connect(self._handle_burnout_update)
        self.widget.break_requested.connect(self._show_break_popup)
        self.widget.stats_requested.connect(self._show_stats)
        self.widget.settings_requested.connect(self._show_settings)
        self.widget.pause_requested.connect(self._on_pause_toggle)
        self.widget.pomodoro_start.connect(self._start_pomodoro)
        self.widget.pomodoro_stop.connect(self._stop_pomodoro)
        self.widget.quit_requested.connect(self._quit)
        self.widget.restart_requested.connect(self._restart)

        # Mode change signals
        self.widget.stt_mode_changed.connect(self._on_stt_mode_changed)
        self.widget.vc_mode_changed.connect(self._on_vc_mode_changed)

        # Module restart signals
        self.widget.stt_restart_requested.connect(self._restart_stt)
        self.widget.vc_restart_requested.connect(self._restart_vc)
        self.widget.hotkeys_restart_requested.connect(self._restart_hotkeys)

        # Sleep/Wake signal
        self.widget.sleep_requested.connect(self._on_sleep_toggle)

        # State
        self._stt_processing = False
        self._vc_processing = False
        self._session_id = None
        self._paused = False
        self._sleeping = False  # Sleep mode - all systems offline
        self._pomodoro_running_before_sleep = None  # Track pomodoro state before sleep
        self._activity_count = 0

        # Health monitoring state
        self._stt_last_activity = None  # Last successful STT operation time
        self._vc_last_activity = None   # Last successful VC operation time
        self._stt_stuck_count = 0       # Count of consecutive stuck detections
        self._vc_stuck_count = 0        # Count of consecutive stuck detections

        # Update timer for burnout status
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_burnout_status)
        self._update_timer.start(30000)

        # Health check timer (every 5 minutes)
        self._health_timer = QTimer()
        self._health_timer.timeout.connect(self._check_module_health)
        self._health_timer.start(300000)  # 5 minutes

    def start(self) -> None:
        """Start all agents."""
        self._start_time = datetime.now()

        logger.info("=" * 50)
        logger.info("  Productivity Hub - Unified Agent")
        logger.info("=" * 50)
        logger.info("Speech-to-Text: Right Shift key (toggle)")
        logger.info("Voice Commander: Option key (hold)")
        if CONFIG.get("wake_word_enabled"):
            logger.info(f"Wake Words: {CONFIG.get('wake_words', [])}")
        logger.info(f"Pomodoro: {CONFIG['work_interval_minutes']}min work / {CONFIG['short_break_minutes']}min break")
        logger.info(f"Log file: {LOG_FILE}")
        logger.info("=" * 50)

        # Load models in background
        self._load_models_async()

        # Start combined hotkey listener
        self.hotkey_manager.start()

        # Start wake word detector if enabled
        if CONFIG.get("wake_word_enabled"):
            self.wake_word_detector.start()

        # Start burnout session
        self._session_id = self.data_store.start_session()
        self.activity_monitor.start()
        self._update_burnout_status()

        # Show widget
        self.widget.show()

    def _load_models_async(self) -> None:
        """Load models in background."""
        def load():
            self.stt_status_changed.emit("processing", "Loading...")
            self.vc_status_changed.emit("processing", "Loading...")

            # Load transcriber (shared model)
            self.stt_transcriber.load_model()
            self.vc_transcriber.load_model()

            self.stt_status_changed.emit("idle", "")
            self.vc_status_changed.emit("idle", "")
            logger.info("Models loaded. Ready!")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    # ===== Speech-to-Text Methods =====

    def _on_stt_recording_start(self) -> None:
        """Start STT recording."""
        logger.info("[STT] Hotkey activated!")
        if self._stt_processing:
            logger.info("[STT] Already processing, ignoring")
            return

        self.stt_status_changed.emit("recording", "")
        self.stt_audio_recorder.start_recording()
        logger.info("[STT] Recording started...")

    def _on_stt_recording_stop(self) -> None:
        """Stop STT recording and process."""
        logger.info("[STT] Hotkey released!")
        if not self.stt_audio_recorder.is_recording():
            logger.info("[STT] Not recording, ignoring release")
            return

        logger.info("[STT] Processing audio...")
        self._stt_processing = True
        self.stt_status_changed.emit("processing", "")

        audio = self.stt_audio_recorder.stop_recording()

        def transcribe():
            try:
                if audio.size == 0:
                    self.stt_status_changed.emit("error", "No audio")
                    self._stt_processing = False
                    return

                text = self.stt_transcriber.transcribe(audio, CONFIG["sample_rate"])

                if text:
                    self.stt_transcription_complete.emit(text)
                else:
                    self.stt_status_changed.emit("error", "No speech")
                    self._stt_processing = False

            except Exception as e:
                logger.info(f"[STT] Error: {e}")
                self.stt_status_changed.emit("error", "Error")
                self._stt_processing = False

        thread = threading.Thread(target=transcribe, daemon=True)
        thread.start()

    def _on_stt_transcription_done(self, text: str) -> None:
        """Handle STT transcription complete."""
        logger.info(f"[STT] Transcribed: {text}")
        logger.info(f"[STT] Outputting text (mode: {self.output_handler.mode})...")
        self.output_handler.output(text)
        logger.info(f"[STT] Text output complete!")
        word_count = len(text.split())

        # Log to audit trail
        self.command_logger.log_stt_transcription(text, word_count)

        self.stt_status_changed.emit("done", f"{word_count} words")

        QTimer.singleShot(2000, lambda: self.stt_status_changed.emit("idle", ""))
        self._stt_processing = False

    def _on_stt_mode_changed(self, mode: str) -> None:
        """Handle STT mode change."""
        self.hotkey_manager.set_activation_mode("stt", mode)
        logger.info(f"[STT] Mode changed to: {mode}")

    # ===== Voice Commander Methods =====

    def _on_vc_recording_start(self) -> None:
        """Start VC recording."""
        logger.info("[VC] Hotkey activated!")
        if self._vc_processing:
            logger.info("[VC] Already processing, ignoring")
            return

        self.vc_status_changed.emit("listening", "")
        self.vc_audio_recorder.start_recording()
        logger.info("[VC] Listening...")

    def _on_vc_recording_stop(self) -> None:
        """Stop VC recording and process."""
        logger.info("[VC] Hotkey released!")
        if not self.vc_audio_recorder.is_recording():
            logger.info("[VC] Not recording, ignoring release")
            return

        logger.info("[VC] Processing audio...")
        self._vc_processing = True
        self.vc_status_changed.emit("processing", "")

        audio = self.vc_audio_recorder.stop_recording()

        def process():
            try:
                import time
                start_time = time.time()

                if audio.size == 0:
                    self.vc_status_changed.emit("error", "No audio")
                    self._vc_processing = False
                    return

                text = self.vc_transcriber.transcribe(audio, CONFIG["sample_rate"])

                if not text:
                    self.vc_status_changed.emit("error", "No speech")
                    self._vc_processing = False
                    return

                logger.info(f"[VC] Heard: '{text}'")

                command = self.command_parser.parse(text)
                logger.info(f"[VC] Parsed: {command.command_type.value} - {command.params}")

                self.vc_status_changed.emit("executing", command.command_type.value.replace("_", " ").title())

                success, message = self.action_executor.execute(command)
                logger.info(f"[VC] Result: {success} - {message}")

                # Speak feedback
                feedback_text = get_feedback_text(
                    command.command_type.value,
                    command.params,
                    success
                )
                self.voice_feedback.speak(feedback_text)

                # Log to audit trail
                execution_time_ms = int((time.time() - start_time) * 1000)
                self.command_logger.log_voice_command(
                    transcribed_text=text,
                    command_type=command.command_type.value,
                    command_params=command.params,
                    success=success,
                    result_message=message,
                    execution_time_ms=execution_time_ms
                )

                self.vc_command_executed.emit(success, message)

            except Exception as e:
                logger.info(f"[VC] Error: {e}")
                self.vc_status_changed.emit("error", "Error")
                self._vc_processing = False

        thread = threading.Thread(target=process, daemon=True)
        thread.start()

    def _on_vc_command_executed(self, success: bool, message: str) -> None:
        """Handle VC command execution complete."""
        if success:
            self.vc_status_changed.emit("success", message)
        else:
            self.vc_status_changed.emit("error", message)

        QTimer.singleShot(2000, lambda: self.vc_status_changed.emit("idle", ""))
        self._vc_processing = False

    def _on_vc_mode_changed(self, mode: str) -> None:
        """Handle VC mode change."""
        self.hotkey_manager.set_activation_mode("vc", mode)
        logger.info(f"[VC] Mode changed to: {mode}")

    def _on_wake_word_detected(self) -> None:
        """Handle wake word detection - start VC recording."""
        logger.info("[VC] Wake word detected! Starting voice command...")

        # Pause wake word detection while processing command
        self.wake_word_detector.pause()

        # Speak acknowledgment
        self.voice_feedback.speak("Yes?")

        # Start VC recording
        self._on_vc_recording_start()

        # Auto-stop after 5 seconds of recording
        QTimer.singleShot(5000, self._on_wake_word_timeout)

    def _on_wake_word_timeout(self) -> None:
        """Handle wake word recording timeout."""
        if self.vc_audio_recorder.is_recording():
            logger.info("[VC] Wake word recording timeout, processing...")
            self._on_vc_recording_stop()

        # Resume wake word detection
        self.wake_word_detector.resume()

    # ===== Module Restart and Health Methods =====

    def _restart_stt(self) -> None:
        """Restart STT module to recover from stuck state."""
        logger.info("[STT] Restarting STT module...")
        self.stt_status_changed.emit("processing", "Restarting...")

        try:
            # Stop any ongoing recording
            if self.stt_audio_recorder.is_recording():
                self.stt_audio_recorder.stop_recording()

            # Reset state
            self._stt_processing = False
            self._stt_stuck_count = 0

            # Recreate audio recorder (fresh stream)
            self.stt_audio_recorder = AudioRecorder(
                sample_rate=CONFIG["sample_rate"],
                channels=CONFIG["channels"],
                device=self.settings.get("mic_device"),
            )

            # Recreate transcriber (fresh API connection)
            self.stt_transcriber = Transcriber(
                model_size=CONFIG["model_size"],
                language=CONFIG["language"],
                use_groq=CONFIG.get("use_groq", True),
                groq_api_key=CONFIG.get("groq_api_key"),
            )

            # Reload model in background
            def reload():
                self.stt_transcriber.load_model()
                self._stt_last_activity = datetime.now()
                self.stt_status_changed.emit("idle", "")
                logger.info("[STT] Module restarted successfully!")

            thread = threading.Thread(target=reload, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"[STT] Restart failed: {e}")
            self.stt_status_changed.emit("error", "Restart failed")

    def _restart_vc(self) -> None:
        """Restart VC module to recover from stuck state."""
        logger.info("[VC] Restarting VC module...")
        self.vc_status_changed.emit("processing", "Restarting...")

        try:
            # Stop any ongoing recording
            if self.vc_audio_recorder.is_recording():
                self.vc_audio_recorder.stop_recording()

            # Stop wake word detector temporarily
            wake_word_was_running = self.wake_word_detector.is_running()
            if wake_word_was_running:
                self.wake_word_detector.stop()

            # Reset state
            self._vc_processing = False
            self._vc_stuck_count = 0

            # Recreate audio recorder (fresh stream)
            self.vc_audio_recorder = AudioRecorder(
                sample_rate=CONFIG["sample_rate"],
                channels=CONFIG["channels"],
                device=self.settings.get("mic_device"),
            )

            # Recreate transcriber (fresh API connection)
            self.vc_transcriber = Transcriber(
                model_size=CONFIG["model_size"],
                language=CONFIG["language"],
                use_groq=CONFIG.get("use_groq", True),
                groq_api_key=CONFIG.get("groq_api_key"),
            )

            # Reload model and restart wake word in background
            def reload():
                self.vc_transcriber.load_model()

                # Recreate wake word detector with new transcriber
                if wake_word_was_running:
                    self.wake_word_detector = WakeWordDetector(
                        wake_words=self.settings.get("wake_words", ["hey computer"]),
                        transcriber=self.vc_transcriber,
                        sample_rate=CONFIG["sample_rate"],
                        chunk_duration=2.0,
                        on_wake_word=self._on_wake_word_detected,
                        enabled=self.settings.get("wake_word_enabled", False),
                    )
                    self.wake_word_detector.start()

                self._vc_last_activity = datetime.now()
                self.vc_status_changed.emit("idle", "")
                logger.info("[VC] Module restarted successfully!")

            thread = threading.Thread(target=reload, daemon=True)
            thread.start()

        except Exception as e:
            logger.error(f"[VC] Restart failed: {e}")
            self.vc_status_changed.emit("error", "Restart failed")

    def _restart_hotkeys(self) -> None:
        """Restart the hotkey listener."""
        logger.info("[Hotkeys] Restarting hotkey listener...")
        try:
            self.hotkey_manager.stop()

            # Recreate hotkey manager
            self.hotkey_manager = CombinedHotkeyManager()
            self.hotkey_manager.add_hotkey(
                name="stt",
                hotkey=CONFIG["stt_hotkey"],
                activation_mode=CONFIG["stt_activation_mode"],
                on_activate=self._on_stt_recording_start,
                on_deactivate=self._on_stt_recording_stop,
            )
            self.hotkey_manager.add_hotkey(
                name="vc",
                hotkey=CONFIG["vc_hotkey"],
                activation_mode=CONFIG["vc_activation_mode"],
                on_activate=self._on_vc_recording_start,
                on_deactivate=self._on_vc_recording_stop,
            )
            self.hotkey_manager.start()
            logger.info("[Hotkeys] Hotkey listener restarted successfully!")
        except Exception as e:
            logger.error(f"[Hotkeys] Restart failed: {e}")

    def _check_module_health(self) -> None:
        """Check if STT/VC modules are stuck and auto-recover."""
        if self._sleeping:
            return  # Skip health checks while sleeping

        now = datetime.now()

        # Check STT health
        if self._stt_processing:
            self._stt_stuck_count += 1
            logger.warning(f"[Health] STT appears stuck (count: {self._stt_stuck_count})")
            if self._stt_stuck_count >= 3:  # Stuck for 15+ minutes
                logger.warning("[Health] STT stuck for too long, auto-restarting...")
                self._restart_stt()
        else:
            self._stt_stuck_count = 0

        # Check VC health
        if self._vc_processing:
            self._vc_stuck_count += 1
            logger.warning(f"[Health] VC appears stuck (count: {self._vc_stuck_count})")
            if self._vc_stuck_count >= 3:  # Stuck for 15+ minutes
                logger.warning("[Health] VC stuck for too long, auto-restarting...")
                self._restart_vc()
        else:
            self._vc_stuck_count = 0

        # Log health status periodically
        stt_status = "processing" if self._stt_processing else "idle"
        vc_status = "processing" if self._vc_processing else "idle"
        logger.info(f"[Health] STT: {stt_status}, VC: {vc_status}, Uptime: {self._get_uptime()}")

    def _get_uptime(self) -> str:
        """Get application uptime as string."""
        if hasattr(self, '_start_time'):
            delta = datetime.now() - self._start_time
            hours, remainder = divmod(int(delta.total_seconds()), 3600)
            minutes, seconds = divmod(remainder, 60)
            return f"{hours}h {minutes}m"
        return "unknown"

    # ===== Sleep/Wake Methods =====

    def _on_sleep_toggle(self, sleeping: bool) -> None:
        """Handle sleep/wake toggle."""
        if sleeping:
            self._sleep()
        else:
            self._wake()

    def _sleep(self) -> None:
        """Put all systems to sleep."""
        if self._sleeping:
            return

        logger.info("=" * 50)
        logger.info("  ENTERING SLEEP MODE")
        logger.info("=" * 50)

        self._sleeping = True

        try:
            # Stop hotkey listener
            logger.info("[Sleep] Stopping hotkey listener...")
            self.hotkey_manager.stop()
        except Exception as e:
            logger.error(f"[Sleep] Error stopping hotkey listener: {e}")

        try:
            # Stop wake word detector
            if self.wake_word_detector and self.wake_word_detector.is_running():
                logger.info("[Sleep] Stopping wake word detector...")
                self.wake_word_detector.stop()
        except Exception as e:
            logger.error(f"[Sleep] Error stopping wake word detector: {e}")

        try:
            # Stop any ongoing recordings
            if self.stt_audio_recorder.is_recording():
                logger.info("[Sleep] Stopping STT recording...")
                self.stt_audio_recorder.stop_recording()
        except Exception as e:
            logger.error(f"[Sleep] Error stopping STT recording: {e}")

        try:
            if self.vc_audio_recorder.is_recording():
                logger.info("[Sleep] Stopping VC recording...")
                self.vc_audio_recorder.stop_recording()
        except Exception as e:
            logger.error(f"[Sleep] Error stopping VC recording: {e}")

        try:
            # Pause pomodoro
            if self.pomodoro:
                status = self.pomodoro.get_status()
                self._pomodoro_running_before_sleep = status.get("state") == "working"
                if self._pomodoro_running_before_sleep:
                    logger.info("[Sleep] Pausing pomodoro...")
                    self.pomodoro.pause()
        except Exception as e:
            logger.error(f"[Sleep] Error pausing pomodoro: {e}")
            self._pomodoro_running_before_sleep = False

        try:
            # Stop activity monitoring
            logger.info("[Sleep] Stopping activity monitor...")
            self.activity_monitor.stop()
        except Exception as e:
            logger.error(f"[Sleep] Error stopping activity monitor: {e}")

        # Stop health check timer
        self._health_timer.stop()

        # Reset processing states
        self._stt_processing = False
        self._vc_processing = False

        logger.info("[Sleep] All systems offline. Widget still visible.")
        logger.info("=" * 50)

    def _wake(self) -> None:
        """Wake up all systems."""
        if not self._sleeping:
            return

        logger.info("=" * 50)
        logger.info("  WAKING UP")
        logger.info("=" * 50)

        self._sleeping = False

        try:
            # Restart hotkey listener
            logger.info("[Wake] Starting hotkey listener...")
            self.hotkey_manager = CombinedHotkeyManager()
            self.hotkey_manager.add_hotkey(
                name="stt",
                hotkey=CONFIG["stt_hotkey"],
                activation_mode=CONFIG["stt_activation_mode"],
                on_activate=self._on_stt_recording_start,
                on_deactivate=self._on_stt_recording_stop,
            )
            self.hotkey_manager.add_hotkey(
                name="vc",
                hotkey=CONFIG["vc_hotkey"],
                activation_mode=CONFIG["vc_activation_mode"],
                on_activate=self._on_vc_recording_start,
                on_deactivate=self._on_vc_recording_stop,
            )
            self.hotkey_manager.start()

            # Restart wake word detector if it was enabled
            wake_word_enabled = self.settings.get("wake_word_enabled", CONFIG.get("wake_word_enabled", False))
            if wake_word_enabled:
                logger.info("[Wake] Starting wake word detector...")
                try:
                    self.wake_word_detector = WakeWordDetector(
                        wake_words=self.settings.get("wake_words", CONFIG.get("wake_words", ["hey computer"])),
                        transcriber=self.vc_transcriber,
                        sample_rate=CONFIG["sample_rate"],
                        chunk_duration=2.0,
                        on_wake_word=self._on_wake_word_detected,
                        enabled=True,
                    )
                    self.wake_word_detector.start()
                except Exception as e:
                    logger.error(f"[Wake] Failed to start wake word detector: {e}")

            # Resume pomodoro if it was running
            if hasattr(self, '_pomodoro_running_before_sleep') and self._pomodoro_running_before_sleep:
                logger.info("[Wake] Resuming pomodoro...")
                try:
                    self.pomodoro.resume()
                except Exception as e:
                    logger.error(f"[Wake] Failed to resume pomodoro: {e}")
                self._pomodoro_running_before_sleep = None

            # Restart activity monitoring
            logger.info("[Wake] Starting activity monitor...")
            self.activity_monitor.start()

            # Restart health check timer
            self._health_timer.start(300000)

            # Update status
            self.stt_status_changed.emit("idle", "")
            self.vc_status_changed.emit("idle", "")

            try:
                self._update_burnout_status()
            except Exception as e:
                logger.error(f"[Wake] Failed to update burnout status: {e}")

            logger.info("[Wake] All systems online!")
            logger.info("=" * 50)

        except Exception as e:
            logger.error(f"[Wake] Critical error during wake: {e}")
            import traceback
            logger.error(traceback.format_exc())

    # ===== Burnout Monitor Methods =====

    def _on_activity(self, event_type: str, file_path: str, project: str) -> None:
        """Handle activity event."""
        if self._paused or self._sleeping:
            return

        self.data_store.log_activity(
            event_type=event_type,
            file_path=file_path,
            project=project,
        )

        self._activity_count += 1

        if self._activity_count % 10 == 0:
            self._update_burnout_status()

    def _update_burnout_status(self) -> None:
        """Update burnout status."""
        if self._paused:
            return

        try:
            status_data = self.analysis.get_status()

            if self.pomodoro:
                pomo_status = self.pomodoro.get_status()
                status_data["pomodoro_state"] = pomo_status["state"]
                status_data["remaining_seconds"] = pomo_status["remaining_seconds"]
                status_data["pomodoro_count"] = pomo_status["total_today"]

            self.burnout_status_update.emit(status_data["status"], status_data)
        except Exception as e:
            logger.error(f"Error updating burnout status: {e}")

    def _handle_burnout_update(self, status: str, data: dict) -> None:
        """Handle burnout status update in UI."""
        try:
            self.widget.set_pomodoro_status(status, data)
        except Exception as e:
            logger.error(f"Error updating UI: {e}")

    def _start_pomodoro(self) -> None:
        """Start pomodoro session."""
        if self.pomodoro:
            self.pomodoro.start_work()
            logger.info(f"[Pomodoro] Started! Focus for {CONFIG['work_interval_minutes']} minutes.")
            if self.settings.get("play_sound", True):
                SoundPlayer.play_gentle()
            self._update_burnout_status()

    def _stop_pomodoro(self) -> None:
        """Stop pomodoro session."""
        if self.pomodoro:
            self.pomodoro.stop()
            logger.info("[Pomodoro] Stopped.")
            self._update_burnout_status()

    def _on_pomodoro_tick(self, remaining_seconds: int) -> None:
        """Handle pomodoro tick."""
        self._update_burnout_status()

    def _on_work_complete(self, count: int) -> None:
        """Handle work session complete."""
        logger.info(f"[Pomodoro] #{count} complete!")

    def _on_pomodoro_break(self, break_type: str, duration: int, count: int) -> None:
        """Handle pomodoro break time."""
        logger.info(f"[Pomodoro] Time for a {break_type} break! ({duration} min)")

        if self.settings.get("play_sound", True):
            SoundPlayer.play_alarm(repeat=3, interval=0.4)

        if self.settings.get("show_popup", True):
            popup = BreakPopup(
                break_type=break_type,
                duration_minutes=duration,
                pomodoro_count=count,
            )
            popup.break_started.connect(lambda mins: self._start_break_timer(mins))
            popup.break_skipped.connect(self._on_break_skipped)
            popup.exec()
        else:
            self._start_break_timer(duration)

    def _show_break_popup(self) -> None:
        """Show manual break popup."""
        duration = CONFIG.get("short_break_minutes", 5)

        if self.settings.get("play_sound", True):
            SoundPlayer.play_gentle()

        if self.settings.get("show_popup", True):
            popup = BreakPopup(
                break_type="short",
                duration_minutes=duration,
                pomodoro_count=self.pomodoro.total_pomodoros_today if self.pomodoro else 0,
            )
            popup.break_started.connect(lambda mins: self._start_break_timer(mins))
            popup.break_skipped.connect(self._on_break_skipped)
            popup.exec()
        else:
            self._start_break_timer(duration)

    def _start_break_timer(self, duration_minutes: int) -> None:
        """Start break timer."""
        if self.pomodoro:
            self.pomodoro.start_break("short" if duration_minutes <= 5 else "long")

        extend_minutes = CONFIG.get("break_extend_minutes", 5)
        self.break_timer_popup = BreakTimerPopup(duration_minutes, extend_minutes)
        self.break_timer_popup.break_ended.connect(self._on_break_ended)
        self.break_timer_popup.break_extended.connect(self._on_break_extended)
        self.break_timer_popup.show()

        self.data_store.log_break(duration_minutes)
        self._update_burnout_status()

    def _on_break_ended(self) -> None:
        """Handle break end."""
        logger.info("[Pomodoro] Break ended! Ready to focus.")
        self.break_timer_popup = None
        self._update_burnout_status()

    def _on_break_extended(self, minutes: int) -> None:
        """Handle break extension."""
        logger.info(f"[Pomodoro] Break extended by {minutes} minutes.")
        self.data_store.log_break(minutes)

    def _on_break_skipped(self) -> None:
        """Handle break skip."""
        logger.info("[Pomodoro] Break skipped.")
        self._update_burnout_status()

    def _show_stats(self) -> None:
        """Show stats dialog."""
        daily = self.analysis.get_daily_summary()
        weekly = self.analysis.get_weekly_summary()

        if self.pomodoro:
            daily["pomodoros"] = self.pomodoro.total_pomodoros_today

        dialog = StatsDialog(daily, weekly, self.widget)
        dialog.exec()

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings, self.widget)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, new_settings: dict) -> None:
        """Apply new settings."""
        try:
            self.settings = new_settings

            if self.pomodoro:
                self.pomodoro.work_minutes = self.settings.get("pomodoro_work_minutes", 25)
                self.pomodoro.short_break_minutes = self.settings.get("pomodoro_short_break", 5)
                self.pomodoro.long_break_minutes = self.settings.get("pomodoro_long_break", 15)

            # Update voice feedback settings
            self.voice_feedback.set_enabled(self.settings.get("speak_feedback", True))
            self.voice_feedback.set_voice(self.settings.get("voice_feedback_voice", "Alex"))
            self.voice_feedback.set_rate(self.settings.get("voice_feedback_rate", 200))

            # Update wake word settings
            wake_word_enabled = self.settings.get("wake_word_enabled", False)
            wake_words = self.settings.get("wake_words", ["hey computer"])

            # Update wake words list
            self.wake_word_detector.set_wake_words(wake_words)

            # Enable/disable wake word detector
            if wake_word_enabled and not self.wake_word_detector.is_running():
                self.wake_word_detector.set_enabled(True)
                self.wake_word_detector.start()
                logger.info(f"Wake word detection enabled: {wake_words}")
            elif not wake_word_enabled and self.wake_word_detector.is_running():
                self.wake_word_detector.stop()
                self.wake_word_detector.set_enabled(False)
                logger.info("Wake word detection disabled")

            self.analysis.config = self.settings
            logger.info("Settings updated!")
            self._update_burnout_status()
        except Exception as e:
            logger.error(f"Error applying settings: {e}")

    def _on_pause_toggle(self, paused: bool) -> None:
        """Handle pause toggle."""
        self._paused = paused
        if paused:
            logger.info("Tracking paused")
            if self.pomodoro:
                self.pomodoro.pause()
        else:
            logger.info("Tracking resumed")
            if self.pomodoro:
                self.pomodoro.resume()
            self._update_burnout_status()

    def _quit(self) -> None:
        """Quit the application."""
        logger.info("Shutting down Productivity Hub...")

        # Stop hotkeys
        self.hotkey_manager.stop()

        # Stop wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.stop()

        # Stop burnout
        if self._session_id:
            self.data_store.end_session(self._session_id)
        if self.pomodoro:
            self.pomodoro.stop()
        self.activity_monitor.stop()
        self.data_store.cleanup_old_data(self.settings.get("data_retention_days", 90))

        QApplication.quit()

    def _restart(self) -> None:
        """Restart the application."""
        import subprocess
        logger.info("Restarting Productivity Hub...")

        # Stop hotkeys
        self.hotkey_manager.stop()

        # Stop wake word detector
        if self.wake_word_detector:
            self.wake_word_detector.stop()

        # Stop burnout
        if self._session_id:
            self.data_store.end_session(self._session_id)
        if self.pomodoro:
            self.pomodoro.stop()
        self.activity_monitor.stop()

        # Launch new instance
        script_path = Path(__file__).parent / "main.py"
        subprocess.Popen(
            [sys.executable, str(script_path)],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # Quit current instance
        QApplication.quit()


def main():
    """Entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Productivity Hub")

    hub = ProductivityHub()
    hub.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
