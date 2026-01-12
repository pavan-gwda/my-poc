#!/usr/bin/env python3
"""
Burnout Monitor
A friendly tool that tracks your coding activity, runs Pomodoro timer,
and reminds you to take breaks with sound and popup notifications.
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer, QObject, pyqtSignal

from config import CONFIG
from core import DataStore, ActivityMonitor, AnalysisEngine, PomodoroTimer
from ui import FloatingWidget, StatsDialog, BreakPopup, BreakTimerPopup, SettingsDialog
from ui.break_popup import SoundPlayer


class BurnoutMonitor(QObject):
    """Main application controller."""

    # Signals for thread-safe updates
    status_update = pyqtSignal(str, dict)

    def __init__(self):
        super().__init__()

        # Load saved settings (merges with defaults)
        self.settings = SettingsDialog.load_settings()

        # Initialize components
        self.data_store = DataStore()
        self.analysis = AnalysisEngine(self.data_store, self.settings)

        # Activity monitor
        watch_dirs = self.settings.get("watch_directories") or [str(Path.home() / "projects")]
        self.activity_monitor = ActivityMonitor(
            on_activity=self._on_activity,
            watch_directories=watch_dirs,
            exclude_directories=set(self.settings.get("exclude_directories", [])),
        )

        # Pomodoro timer
        self.pomodoro = None
        if self.settings.get("pomodoro_enabled", True):
            self.pomodoro = PomodoroTimer(
                work_minutes=self.settings.get("pomodoro_work_minutes", 25),
                short_break_minutes=self.settings.get("pomodoro_short_break", 5),
                long_break_minutes=self.settings.get("pomodoro_long_break", 15),
                pomodoros_until_long_break=self.settings.get("pomodoros_until_long_break", 4),
                data_store=self.data_store,  # Pass data store for persistence
            )
            self.pomodoro.tick.connect(self._on_pomodoro_tick)
            self.pomodoro.break_time.connect(self._on_pomodoro_break)
            self.pomodoro.work_session_complete.connect(self._on_work_complete)

        # UI
        self.widget = FloatingWidget(
            opacity=self.settings.get("widget_opacity", 0.95),
            position=self.settings.get("widget_position", "top-right"),
            pomodoro_enabled=self.settings.get("pomodoro_enabled", True),
        )

        # Break timer popup (shown during breaks)
        self.break_timer_popup = None

        # Connect signals
        self.status_update.connect(self.widget.set_status)
        self.widget.break_requested.connect(self._show_break_popup)
        self.widget.stats_requested.connect(self._show_stats)
        self.widget.settings_requested.connect(self._show_settings)
        self.widget.pause_requested.connect(self._on_pause_toggle)
        self.widget.quit_requested.connect(self._quit)
        self.widget.pomodoro_start.connect(self._start_pomodoro)
        self.widget.pomodoro_stop.connect(self._stop_pomodoro)

        # State
        self._session_id = None
        self._paused = False
        self._activity_count = 0

        # Update timer (every 30 seconds)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._update_status)
        self._update_timer.start(30000)

    def start(self) -> None:
        """Start the monitor."""
        print("Burnout Monitor starting...")
        print(f"Pomodoro: {self.settings.get('pomodoro_work_minutes', 25)} min work / {self.settings.get('pomodoro_short_break', 5)} min break")
        print(f"Sound: {'Enabled' if self.settings.get('play_sound', True) else 'Disabled'}")
        print(f"Popup: {'Enabled' if self.settings.get('show_popup', True) else 'Disabled'}")
        print()
        print("Double-click widget to start Pomodoro!")
        print("Right-click for menu.")
        print()

        # Start session
        self._session_id = self.data_store.start_session()

        # Start activity monitoring
        self.activity_monitor.start()

        # Initial status update
        self._update_status()

        # Show widget
        self.widget.show()

    def _on_activity(self, event_type: str, file_path: str, project: str) -> None:
        """Handle activity events from monitor."""
        if self._paused:
            return

        self.data_store.log_activity(
            event_type=event_type,
            file_path=file_path,
            project=project,
        )

        self._activity_count += 1

        # Update UI every 10 activities
        if self._activity_count % 10 == 0:
            self._update_status()

    def _update_status(self) -> None:
        """Update the widget status."""
        if self._paused:
            return

        status_data = self.analysis.get_status()

        # Add pomodoro state
        if self.pomodoro:
            pomo_status = self.pomodoro.get_status()
            status_data["pomodoro_state"] = pomo_status["state"]
            status_data["remaining_seconds"] = pomo_status["remaining_seconds"]
            status_data["pomodoro_count"] = pomo_status["total_today"]

        self.status_update.emit(status_data["status"], status_data)

    def _start_pomodoro(self) -> None:
        """Start a pomodoro work session."""
        if self.pomodoro:
            self.pomodoro.start_work()
            print(f"Pomodoro started! Focus for {self.settings.get('pomodoro_work_minutes', 25)} minutes.")
            if self.settings.get("play_sound", True):
                SoundPlayer.play_gentle()  # Gentle sound for start
            self._update_status()

    def _stop_pomodoro(self) -> None:
        """Stop the current pomodoro."""
        if self.pomodoro:
            self.pomodoro.stop()
            print("Pomodoro stopped.")
            self._update_status()

    def _on_pomodoro_tick(self, remaining_seconds: int) -> None:
        """Handle pomodoro timer tick."""
        if self.pomodoro:
            pomo_status = self.pomodoro.get_status()
            self.widget.update_pomodoro_tick(
                remaining_seconds,
                pomo_status["total_today"],
                pomo_status["state"]
            )

    def _on_work_complete(self, count: int) -> None:
        """Handle work session completion."""
        print(f"Pomodoro #{count} complete!")

    def _on_pomodoro_break(self, break_type: str, duration: int, count: int) -> None:
        """Handle pomodoro break time."""
        print(f"Time for a {break_type} break! ({duration} min)")

        # Play alarming sound - time to take a break!
        if self.settings.get("play_sound", True):
            SoundPlayer.play_alarm(repeat=3, interval=0.4)

        # Show popup
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
            # Auto-start break without popup
            self._start_break_timer(duration)

    def _show_break_popup(self) -> None:
        """Show break popup (manual break request)."""
        duration = self.settings.get("pomodoro_short_break", 5)

        if self.settings.get("play_sound", True):
            SoundPlayer.play_gentle()  # Gentle sound for manual break request

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
        """Start the break timer popup."""
        if self.pomodoro:
            self.pomodoro.start_break("short" if duration_minutes <= 5 else "long")

        extend_minutes = self.settings.get("break_extend_minutes", 5)
        self.break_timer_popup = BreakTimerPopup(duration_minutes, extend_minutes)
        self.break_timer_popup.break_ended.connect(self._on_break_ended)
        self.break_timer_popup.break_extended.connect(self._on_break_extended)
        self.break_timer_popup.show()

        # Log the break
        self.data_store.log_break(duration_minutes)

        self._update_status()

    def _on_break_ended(self) -> None:
        """Handle break end."""
        print("Break ended! Ready to focus.")
        self.break_timer_popup = None
        self._update_status()

    def _on_break_extended(self, minutes: int) -> None:
        """Handle break extension."""
        print(f"Break extended by {minutes} minutes.")
        # Log the extension
        self.data_store.log_break(minutes)

    def _on_break_skipped(self) -> None:
        """Handle break skip."""
        print("Break skipped.")
        self._update_status()

    def _show_stats(self) -> None:
        """Show statistics dialog."""
        daily = self.analysis.get_daily_summary()
        weekly = self.analysis.get_weekly_summary()

        # Add pomodoro count
        if self.pomodoro:
            daily["pomodoros"] = self.pomodoro.total_pomodoros_today

        dialog = StatsDialog(daily, weekly, self.widget)
        dialog.exec()

    def _on_pause_toggle(self, paused: bool) -> None:
        """Handle pause/resume."""
        self._paused = paused
        if paused:
            print("Tracking paused")
            if self.pomodoro:
                self.pomodoro.pause()
        else:
            print("Tracking resumed")
            if self.pomodoro:
                self.pomodoro.resume()
            self._update_status()

    def _quit(self) -> None:
        """Quit the application."""
        print("Shutting down...")

        # End current session
        if self._session_id:
            self.data_store.end_session(self._session_id)

        # Stop pomodoro
        if self.pomodoro:
            self.pomodoro.stop()

        # Stop monitoring
        self.activity_monitor.stop()

        # Cleanup old data
        self.data_store.cleanup_old_data(self.settings.get("data_retention_days", 90))

        QApplication.quit()

    def _show_settings(self) -> None:
        """Show settings dialog."""
        dialog = SettingsDialog(self.settings, self.widget)
        dialog.settings_changed.connect(self._apply_settings)
        dialog.exec()

    def _apply_settings(self, new_settings: dict) -> None:
        """Apply new settings."""
        old_pomodoro_enabled = self.settings.get("pomodoro_enabled", True)
        self.settings = new_settings

        # Update pomodoro timer if settings changed
        if self.pomodoro:
            self.pomodoro.work_minutes = self.settings.get("pomodoro_work_minutes", 25)
            self.pomodoro.short_break_minutes = self.settings.get("pomodoro_short_break", 5)
            self.pomodoro.long_break_minutes = self.settings.get("pomodoro_long_break", 15)
            self.pomodoro.pomodoros_until_long_break = self.settings.get("pomodoros_until_long_break", 4)

        # Handle pomodoro enable/disable
        if self.settings.get("pomodoro_enabled", True) and not old_pomodoro_enabled:
            # Enable pomodoro
            self.pomodoro = PomodoroTimer(
                work_minutes=self.settings.get("pomodoro_work_minutes", 25),
                short_break_minutes=self.settings.get("pomodoro_short_break", 5),
                long_break_minutes=self.settings.get("pomodoro_long_break", 15),
                pomodoros_until_long_break=self.settings.get("pomodoros_until_long_break", 4),
                data_store=self.data_store,  # Pass data store for persistence
            )
            self.pomodoro.tick.connect(self._on_pomodoro_tick)
            self.pomodoro.break_time.connect(self._on_pomodoro_break)
            self.pomodoro.work_session_complete.connect(self._on_work_complete)
            self.widget._pomodoro_enabled = True
        elif not self.settings.get("pomodoro_enabled", True) and old_pomodoro_enabled:
            # Disable pomodoro
            if self.pomodoro:
                self.pomodoro.stop()
                self.pomodoro = None
            self.widget._pomodoro_enabled = False

        # Update analysis engine
        self.analysis.config = self.settings

        print("Settings updated!")
        self._update_status()


def main():
    """Entry point."""
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setApplicationName("Burnout Monitor")

    monitor = BurnoutMonitor()
    monitor.start()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
