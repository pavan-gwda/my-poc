"""Pomodoro timer implementation."""

from PyQt6.QtCore import QObject, QTimer, pyqtSignal
from typing import Optional, TYPE_CHECKING
from enum import Enum

if TYPE_CHECKING:
    from .data_store import DataStore


class PomodoroState(Enum):
    """Pomodoro timer states."""
    IDLE = "idle"
    WORKING = "working"
    SHORT_BREAK = "short_break"
    LONG_BREAK = "long_break"
    PAUSED = "paused"


class PomodoroTimer(QObject):
    """Pomodoro technique timer."""

    # Signals
    state_changed = pyqtSignal(str, int, int)  # state, remaining_seconds, pomodoro_count
    work_session_complete = pyqtSignal(int)  # pomodoro_count
    break_time = pyqtSignal(str, int, int)  # break_type, duration_minutes, pomodoro_count
    tick = pyqtSignal(int)  # remaining_seconds

    def __init__(
        self,
        work_minutes: int = 25,
        short_break_minutes: int = 5,
        long_break_minutes: int = 15,
        pomodoros_until_long_break: int = 4,
        data_store: Optional["DataStore"] = None,
    ):
        super().__init__()

        self.work_minutes = work_minutes
        self.short_break_minutes = short_break_minutes
        self.long_break_minutes = long_break_minutes
        self.pomodoros_until_long_break = pomodoros_until_long_break
        self._data_store = data_store

        self._state = PomodoroState.IDLE
        self._pomodoro_count = 0
        self._total_pomodoros_today = 0
        self._remaining_seconds = 0
        self._paused_state: Optional[PomodoroState] = None

        self._timer = QTimer()
        self._timer.timeout.connect(self._tick)

        # Load today's pomodoro count from database
        self._load_today_count()

    @property
    def state(self) -> PomodoroState:
        return self._state

    @property
    def pomodoro_count(self) -> int:
        return self._pomodoro_count

    @property
    def total_pomodoros_today(self) -> int:
        return self._total_pomodoros_today

    @property
    def remaining_seconds(self) -> int:
        return self._remaining_seconds

    @property
    def remaining_minutes(self) -> int:
        return self._remaining_seconds // 60

    def start_work(self) -> None:
        """Start a work session."""
        self._state = PomodoroState.WORKING
        self._remaining_seconds = self.work_minutes * 60
        self._timer.start(1000)
        self._emit_state()

    def start_break(self, break_type: str = "short") -> None:
        """Start a break."""
        if break_type == "long":
            self._state = PomodoroState.LONG_BREAK
            self._remaining_seconds = self.long_break_minutes * 60
        else:
            self._state = PomodoroState.SHORT_BREAK
            self._remaining_seconds = self.short_break_minutes * 60

        self._timer.start(1000)
        self._emit_state()

    def pause(self) -> None:
        """Pause the timer."""
        if self._state in (PomodoroState.WORKING, PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            self._paused_state = self._state
            self._state = PomodoroState.PAUSED
            self._timer.stop()
            self._emit_state()

    def resume(self) -> None:
        """Resume the timer."""
        if self._state == PomodoroState.PAUSED and self._paused_state:
            self._state = self._paused_state
            self._paused_state = None
            self._timer.start(1000)
            self._emit_state()

    def stop(self) -> None:
        """Stop the timer completely."""
        self._timer.stop()
        self._state = PomodoroState.IDLE
        self._remaining_seconds = 0
        self._emit_state()

    def skip(self) -> None:
        """Skip current session/break."""
        self._timer.stop()

        if self._state == PomodoroState.WORKING:
            # Skip work session, don't count it
            self._state = PomodoroState.IDLE
        elif self._state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            # Skip break, ready for next work session
            self._state = PomodoroState.IDLE

        self._remaining_seconds = 0
        self._emit_state()

    def reset_daily_count(self) -> None:
        """Reset daily pomodoro count."""
        self._total_pomodoros_today = 0
        self._pomodoro_count = 0

    def _load_today_count(self) -> None:
        """Load today's pomodoro count from database."""
        if self._data_store:
            stats = self._data_store.get_today_pomodoros()
            self._total_pomodoros_today = stats["count"]
            # Set cycle count based on total (for long break calculation)
            self._pomodoro_count = self._total_pomodoros_today % self.pomodoros_until_long_break
            print(f"Loaded {self._total_pomodoros_today} pomodoros from today")

    def _save_pomodoro(self) -> None:
        """Save completed pomodoro to database."""
        if self._data_store:
            self._data_store.log_pomodoro(self.work_minutes)

    def _tick(self) -> None:
        """Handle timer tick."""
        self._remaining_seconds -= 1
        self.tick.emit(self._remaining_seconds)

        if self._remaining_seconds <= 0:
            self._timer.stop()
            self._on_session_complete()

    def _on_session_complete(self) -> None:
        """Handle session completion."""
        if self._state == PomodoroState.WORKING:
            # Work session complete
            self._pomodoro_count += 1
            self._total_pomodoros_today += 1

            # Save to database
            self._save_pomodoro()

            self.work_session_complete.emit(self._pomodoro_count)

            # Determine break type
            if self._pomodoro_count >= self.pomodoros_until_long_break:
                self._pomodoro_count = 0  # Reset cycle
                self.break_time.emit("long", self.long_break_minutes, self._total_pomodoros_today)
            else:
                self.break_time.emit("short", self.short_break_minutes, self._total_pomodoros_today)

            self._state = PomodoroState.IDLE

        elif self._state in (PomodoroState.SHORT_BREAK, PomodoroState.LONG_BREAK):
            # Break complete, ready for work
            self._state = PomodoroState.IDLE

        self._emit_state()

    def _emit_state(self) -> None:
        """Emit current state."""
        self.state_changed.emit(
            self._state.value,
            self._remaining_seconds,
            self._total_pomodoros_today
        )

    def get_status(self) -> dict:
        """Get current status as dict."""
        return {
            "state": self._state.value,
            "remaining_seconds": self._remaining_seconds,
            "remaining_minutes": self.remaining_minutes,
            "pomodoro_count": self._pomodoro_count,
            "total_today": self._total_pomodoros_today,
            "is_running": self._timer.isActive(),
        }
