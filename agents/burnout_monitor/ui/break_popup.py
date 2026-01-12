"""Break popup dialog - full screen attention-grabbing break reminder."""

import subprocess
import platform
import threading
import time
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QApplication,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont


class SoundPlayer:
    """Plays alarming notification sounds."""

    @staticmethod
    def play_alarm(repeat: int = 3, interval: float = 0.5):
        """Play an alarming sound multiple times."""
        def _play():
            system = platform.system()
            for i in range(repeat):
                try:
                    if system == "Darwin":  # macOS
                        # Use Funk sound which is more attention-grabbing
                        subprocess.run(
                            ["afplay", "/System/Library/Sounds/Funk.aiff"],
                            capture_output=True,
                            timeout=5
                        )
                    elif system == "Linux":
                        subprocess.run(
                            ["paplay", "/usr/share/sounds/freedesktop/stereo/alarm-clock-elapsed.oga"],
                            capture_output=True,
                            timeout=5
                        )
                    elif system == "Windows":
                        import winsound
                        winsound.MessageBeep(winsound.MB_ICONEXCLAMATION)
                    if i < repeat - 1:
                        time.sleep(interval)
                except Exception:
                    pass

        # Run in background thread to not block UI
        thread = threading.Thread(target=_play, daemon=True)
        thread.start()

    @staticmethod
    def play_gentle():
        """Play a gentle notification sound."""
        system = platform.system()
        try:
            if system == "Darwin":
                subprocess.run(
                    ["afplay", "/System/Library/Sounds/Glass.aiff"],
                    capture_output=True,
                    timeout=5
                )
            elif system == "Linux":
                subprocess.run(
                    ["paplay", "/usr/share/sounds/freedesktop/stereo/complete.oga"],
                    capture_output=True,
                    timeout=5
                )
            elif system == "Windows":
                import winsound
                winsound.MessageBeep()
        except Exception:
            pass


class BreakPopup(QDialog):
    """Full-screen break reminder popup."""

    break_started = pyqtSignal(int)  # duration in minutes
    break_skipped = pyqtSignal()

    def __init__(self, break_type: str = "short", duration_minutes: int = 5, pomodoro_count: int = 0, parent=None):
        super().__init__(parent)
        self.duration_minutes = duration_minutes
        self.break_type = break_type
        self.pomodoro_count = pomodoro_count
        self._setup_ui()

    def _setup_ui(self) -> None:
        """Set up the popup UI."""
        # Make it a prominent window
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)

        # Get screen size for centering
        screen = QApplication.primaryScreen()
        if screen:
            screen_size = screen.availableGeometry()
            width = min(500, screen_size.width() - 100)
            height = min(350, screen_size.height() - 100)
            self.setFixedSize(width, height)
            # Center on screen
            x = (screen_size.width() - width) // 2
            y = (screen_size.height() - height) // 2
            self.move(x, y)

        layout = QVBoxLayout()
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Icon/Emoji
        icon_label = QLabel("☕" if self.break_type == "short" else "🧘")
        icon_font = QFont()
        icon_font.setPointSize(64)
        icon_label.setFont(icon_font)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)

        # Title
        if self.break_type == "long":
            title_text = "Time for a Long Break!"
        else:
            title_text = "Time for a Break!"

        title = QLabel(title_text)
        title_font = QFont()
        title_font.setPointSize(28)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Subtitle
        if self.pomodoro_count > 0:
            subtitle_text = f"Great work! You completed {self.pomodoro_count} pomodoro{'s' if self.pomodoro_count > 1 else ''}."
        else:
            subtitle_text = "You've been working hard. Take a moment to rest."

        subtitle = QLabel(subtitle_text)
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        # Duration info
        duration_text = f"Suggested break: {self.duration_minutes} minutes"
        duration_label = QLabel(duration_text)
        duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(duration_label)

        layout.addStretch()

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        # Take break button
        take_break_btn = QPushButton(f"Take {self.duration_minutes} min Break")
        take_break_btn.setFixedHeight(50)
        take_break_btn.clicked.connect(self._start_break)
        button_layout.addWidget(take_break_btn)

        # Skip button
        skip_btn = QPushButton("Skip")
        skip_btn.setFixedHeight(50)
        skip_btn.clicked.connect(self._skip_break)
        button_layout.addWidget(skip_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a2e;
                border-radius: 20px;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 12px 24px;
                border-radius: 8px;
                font-size: 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:last-child {
                background-color: #555555;
            }
            QPushButton:last-child:hover {
                background-color: #666666;
            }
        """)

    def _start_break(self) -> None:
        """Start the break."""
        self.break_started.emit(self.duration_minutes)
        self.accept()

    def _skip_break(self) -> None:
        """Skip the break."""
        self.break_skipped.emit()
        self.reject()

    @staticmethod
    def play_sound(alarm: bool = True):
        """Play a notification sound."""
        if alarm:
            SoundPlayer.play_alarm(repeat=3, interval=0.4)
        else:
            SoundPlayer.play_gentle()


class BreakTimerPopup(QDialog):
    """Popup showing break countdown timer."""

    break_ended = pyqtSignal()
    break_extended = pyqtSignal(int)  # extra minutes added

    def __init__(self, duration_minutes: int = 5, extend_minutes: int = 5, parent=None):
        super().__init__(parent)
        self.duration_seconds = duration_minutes * 60
        self.remaining_seconds = self.duration_seconds
        self.extend_minutes = extend_minutes
        self._setup_ui()
        self._start_timer()

    def _setup_ui(self) -> None:
        """Set up the timer UI."""
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(220, 160)

        # Position at bottom-right
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            self.move(geometry.right() - 240, geometry.bottom() - 180)

        layout = QVBoxLayout()
        layout.setContentsMargins(20, 15, 20, 15)
        layout.setSpacing(10)

        # Title
        title = QLabel("Break Time")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)

        # Timer display
        self.timer_label = QLabel(self._format_time(self.remaining_seconds))
        timer_font = QFont()
        timer_font.setPointSize(32)
        timer_font.setBold(True)
        self.timer_label.setFont(timer_font)
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.timer_label)

        # Buttons layout
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)

        # Extend break button
        extend_btn = QPushButton(f"+{self.extend_minutes} min")
        extend_btn.clicked.connect(self._extend_break)
        extend_btn.setObjectName("extendBtn")
        btn_layout.addWidget(extend_btn)

        # End early button
        end_btn = QPushButton("End Break")
        end_btn.clicked.connect(self._end_break)
        btn_layout.addWidget(end_btn)

        layout.addLayout(btn_layout)

        self.setLayout(layout)

        self.setStyleSheet("""
            QDialog {
                background-color: #1f4a2d;
                border-radius: 12px;
            }
            QLabel {
                color: #6bff8a;
                background-color: transparent;
            }
            QPushButton {
                background-color: #2d6b3d;
                color: white;
                border: none;
                padding: 8px 12px;
                border-radius: 4px;
                font-size: 12px;
            }
            QPushButton:hover {
                background-color: #3d7b4d;
            }
            QPushButton#extendBtn {
                background-color: #4a6b2d;
            }
            QPushButton#extendBtn:hover {
                background-color: #5a7b3d;
            }
        """)

    def _start_timer(self) -> None:
        """Start the countdown timer."""
        self.timer = QTimer()
        self.timer.timeout.connect(self._tick)
        self.timer.start(1000)

    def _tick(self) -> None:
        """Update timer every second."""
        self.remaining_seconds -= 1
        self.timer_label.setText(self._format_time(self.remaining_seconds))

        if self.remaining_seconds <= 0:
            self._break_time_up()

    def _format_time(self, seconds: int) -> str:
        """Format seconds as MM:SS."""
        mins = seconds // 60
        secs = seconds % 60
        return f"{mins:02d}:{secs:02d}"

    def _extend_break(self) -> None:
        """Extend the break by configured minutes."""
        self.remaining_seconds += self.extend_minutes * 60
        self.timer_label.setText(self._format_time(self.remaining_seconds))
        self.break_extended.emit(self.extend_minutes)
        SoundPlayer.play_gentle()  # Gentle sound to confirm extension

    def _break_time_up(self) -> None:
        """Called when break timer reaches zero."""
        self.timer.stop()
        SoundPlayer.play_alarm(repeat=4, interval=0.3)  # Alarming sound when break ends
        self.break_ended.emit()
        self.accept()

    def _end_break(self) -> None:
        """End the break early (user clicked button)."""
        self.timer.stop()
        SoundPlayer.play_gentle()  # Gentle sound for manual end
        self.break_ended.emit()
        self.accept()
