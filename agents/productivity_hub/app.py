#!/usr/bin/env python3
"""
Productivity Hub - Standalone macOS App
Combines Speech-to-Text, Voice Commander, and Burnout Monitor.
"""

import sys
import os
import threading
import logging
from pathlib import Path
from datetime import datetime

# Setup logging
LOG_DIR = Path.home() / ".productivity_hub" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
LOG_FILE = LOG_DIR / f"productivity_hub_{datetime.now().strftime('%Y%m%d')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
    ]
)
logger = logging.getLogger(__name__)

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONFIG, APP_ALIASES, WEBSITE_SHORTCUTS
from ui.unified_widget import UnifiedWidget

# Import from bundled modules
from modules.stt_core import AudioRecorder, Transcriber, OutputHandler
from modules.vc_core import CommandParser, ActionExecutor, VoiceFeedback, get_feedback_text
from modules.burnout_core import DataStore, ActivityMonitor, AnalysisEngine, PomodoroTimer
from modules.burnout_ui import StatsDialog, BreakPopup, BreakTimerPopup, SettingsDialog
from modules.burnout_ui.break_popup import SoundPlayer

# Import local core
from core import CombinedHotkeyManager, CommandLogger


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
        )

        self.stt_transcriber = Transcriber(
            model_size=CONFIG["model_size"],
            language=CONFIG["language"],
            use_groq=CONFIG.get("use_groq", False),
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
        )

        self.vc_transcriber = Transcriber(
            model_size=CONFIG["model_size"],
            language=CONFIG["language"],
            use_groq=CONFIG.get("use_groq", False),
            groq_api_key=CONFIG.get("groq_api_key"),
        )

        self.command_parser = CommandParser(APP_ALIASES, WEBSITE_SHORTCUTS)
        self.action_executor = ActionExecutor()

        # Command logger for audit trail
        self.command_logger = CommandLogger(
            db_path=Path.home() / ".productivity_hub" / "data" / "command_history.db"
        )

        # Voice feedback for spoken responses
        self.voice_feedback = VoiceFeedback(
            enabled=CONFIG.get("speak_feedback", True),
            voice=CONFIG.get("voice_feedback_voice", "Samantha"),
            rate=CONFIG.get("voice_feedback_rate", 200)
        )

        # ===== Combined Hotkey Manager =====
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

        # ===== Burnout Monitor Components =====
        data_dir = Path.home() / ".productivity_hub" / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.data_store = DataStore(
            db_path=str(data_dir / "burnout.db")
        )
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

        self.break_timer_popup = None

        # Connect signals
        self.stt_status_changed.connect(self.widget.set_stt_status)
        self.stt_transcription_complete.connect(self._on_stt_transcription_done)

        self.vc_status_changed.connect(self.widget.set_vc_status)
        self.vc_command_executed.connect(self._on_vc_command_executed)

        self.burnout_status_update.connect(self._handle_burnout_update)
        self.widget.break_requested.connect(self._show_break_popup)
        self.widget.stats_requested.connect(self._show_stats)
        self.widget.settings_requested.connect(self._show_settings)
        self.widget.pause_requested.connect(self._on_pause_toggle)
        self.widget.pomodoro_start.connect(self._start_pomodoro)
        self.widget.pomodoro_stop.connect(self._stop_pomodoro)
        self.widget.quit_requested.connect(self._quit)
        self.widget.restart_requested.connect(self._restart)

        self.widget.stt_mode_changed.connect(self._on_stt_mode_changed)
        self.widget.vc_mode_changed.connect(self._on_vc_mode_changed)

        # State
        self._stt_processing = False
        self._vc_processing = False
        self._session_id = None
        self._paused = False
        self._activity_count = 0

        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_burnout_status)
        self._update_timer.start(30000)

    def start(self) -> None:
        """Start all agents."""
        logger.info("=" * 50)
        logger.info("  Productivity Hub - Started")
        logger.info("=" * 50)
        logger.info("Speech-to-Text: Right Shift key (hold)")
        logger.info("Voice Commander: Option key (hold)")
        logger.info(f"Pomodoro: {CONFIG['work_interval_minutes']}min work / {CONFIG['short_break_minutes']}min break")

        self._load_models_async()
        self.hotkey_manager.start()

        self._session_id = self.data_store.start_session()
        self.activity_monitor.start()
        self._update_burnout_status()

        self.widget.show()

    def _load_models_async(self) -> None:
        def load():
            self.stt_status_changed.emit("processing", "Loading...")
            self.vc_status_changed.emit("processing", "Loading...")

            self.stt_transcriber.load_model()
            self.vc_transcriber.load_model()

            self.stt_status_changed.emit("idle", "")
            self.vc_status_changed.emit("idle", "")
            logger.info("Models loaded. Ready!")

        thread = threading.Thread(target=load, daemon=True)
        thread.start()

    # ===== Speech-to-Text Methods =====

    def _on_stt_recording_start(self) -> None:
        logger.info("[STT] Hotkey activated!")
        if self._stt_processing:
            return

        self.stt_status_changed.emit("recording", "")
        self.stt_audio_recorder.start_recording()
        logger.info("[STT] Recording started...")

    def _on_stt_recording_stop(self) -> None:
        logger.info("[STT] Hotkey released!")
        if not self.stt_audio_recorder.is_recording():
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
        logger.info(f"[STT] Transcribed: {text}")
        self.output_handler.output(text)
        word_count = len(text.split())
        self.command_logger.log_stt_transcription(text, word_count)
        self.stt_status_changed.emit("done", f"{word_count} words")

        QTimer.singleShot(2000, lambda: self.stt_status_changed.emit("idle", ""))
        self._stt_processing = False

    def _on_stt_mode_changed(self, mode: str) -> None:
        self.hotkey_manager.set_activation_mode("stt", mode)

    # ===== Voice Commander Methods =====

    def _on_vc_recording_start(self) -> None:
        logger.info("[VC] Hotkey activated!")
        if self._vc_processing:
            return

        self.vc_status_changed.emit("listening", "")
        self.vc_audio_recorder.start_recording()
        logger.info("[VC] Listening...")

    def _on_vc_recording_stop(self) -> None:
        logger.info("[VC] Hotkey released!")
        if not self.vc_audio_recorder.is_recording():
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
        if success:
            self.vc_status_changed.emit("success", message)
        else:
            self.vc_status_changed.emit("error", message)

        QTimer.singleShot(2000, lambda: self.vc_status_changed.emit("idle", ""))
        self._vc_processing = False

    def _on_vc_mode_changed(self, mode: str) -> None:
        self.hotkey_manager.set_activation_mode("vc", mode)

    # ===== Burnout Monitor Methods =====

    def _on_activity(self, event_type: str, file_path: str, project: str) -> None:
        if self._paused:
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
        if self._paused:
            return

        status_data = self.analysis.get_status()

        if self.pomodoro:
            pomo_status = self.pomodoro.get_status()
            status_data["pomodoro_state"] = pomo_status["state"]
            status_data["remaining_seconds"] = pomo_status["remaining_seconds"]
            status_data["pomodoro_count"] = pomo_status["total_today"]

        self.burnout_status_update.emit(status_data["status"], status_data)

    def _handle_burnout_update(self, status: str, data: dict) -> None:
        self.widget.set_pomodoro_status(status, data)

    def _start_pomodoro(self) -> None:
        if self.pomodoro:
            self.pomodoro.start_work()
            logger.info(f"[Pomodoro] Started!")
            if self.settings.get("play_sound", True):
                SoundPlayer.play_gentle()
            self._update_burnout_status()

    def _stop_pomodoro(self) -> None:
        if self.pomodoro:
            self.pomodoro.stop()
            logger.info("[Pomodoro] Stopped.")
            self._update_burnout_status()

    def _on_pomodoro_tick(self, remaining_seconds: int) -> None:
        self._update_burnout_status()

    def _on_work_complete(self, count: int) -> None:
        logger.info(f"[Pomodoro] #{count} complete!")

    def _on_pomodoro_break(self, break_type: str, duration: int, count: int) -> None:
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
        logger.info("[Pomodoro] Break ended!")
        self.break_timer_popup = None
        self._update_burnout_status()

    def _on_break_extended(self, minutes: int) -> None:
        logger.info(f"[Pomodoro] Break extended by {minutes} minutes.")
        self.data_store.log_break(minutes)

    def _on_break_skipped(self) -> None:
        logger.info("[Pomodoro] Break skipped.")
        self._update_burnout_status()

    def _show_stats(self) -> None:
        daily = self.analysis.get_daily_summary()
        weekly = self.analysis.get_weekly_summary()

        if self.pomodoro:
            daily["pomodoros"] = self.pomodoro.total_pomodoros_today

        dialog = StatsDialog(daily, weekly, self.widget)
        dialog.exec()

    def _show_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self.widget)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, new_settings: dict) -> None:
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

            self.analysis.config = self.settings
            logger.info("Settings updated!")
            self._update_burnout_status()
        except Exception as e:
            logger.error(f"Error applying settings: {e}")

    def _on_pause_toggle(self, paused: bool) -> None:
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
        logger.info("Shutting down Productivity Hub...")

        self.hotkey_manager.stop()

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

        self.hotkey_manager.stop()

        if self._session_id:
            self.data_store.end_session(self._session_id)
        if self.pomodoro:
            self.pomodoro.stop()
        self.activity_monitor.stop()

        # Launch new instance
        subprocess.Popen(
            [sys.executable, sys.argv[0]],
            start_new_session=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

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
