"""Minimalistic tech-style widget for Burnout Monitor."""

import math
from datetime import datetime
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont, QAction, QPainter, QColor, QBrush, QPen
from typing import Optional, Dict, Any


class ArcProgress(QWidget):
    """Minimal arc progress indicator."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(48, 48)
        self._progress = 0  # 0 to 100
        self._color = QColor("#6b7280")
        self._pulse_phase = 0
        self._is_active = False

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def set_progress(self, value: int, color: str = None, active: bool = False):
        self._progress = max(0, min(100, value))
        if color:
            self._color = QColor(color)
        self._is_active = active
        self.update()

    def _animate(self):
        self._pulse_phase += 0.1
        if self._is_active:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.width() // 2
        radius = 20
        thickness = 3

        # Background arc
        painter.setPen(QPen(QColor(40, 40, 40), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(
            center - radius, center - radius,
            radius * 2, radius * 2,
            0, 360 * 16
        )

        # Progress arc
        if self._progress > 0:
            color = QColor(self._color)
            if self._is_active:
                # Subtle pulse effect
                alpha = int(200 + 55 * math.sin(self._pulse_phase * 2))
                color.setAlpha(alpha)

            painter.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            span = int(self._progress * 3.6 * 16)
            painter.drawArc(
                center - radius, center - radius,
                radius * 2, radius * 2,
                90 * 16, -span
            )


class FloatingWidget(QWidget):
    """Minimalistic tech-style widget for burnout monitoring."""

    # Signals
    break_requested = pyqtSignal()
    stats_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    pause_requested = pyqtSignal(bool)
    pomodoro_start = pyqtSignal()
    pomodoro_stop = pyqtSignal()

    # Status constants
    STATUS_GOOD = "good"
    STATUS_NEEDS_BREAK = "needs_break"
    STATUS_OVERTIME = "overtime"
    STATUS_PAUSED = "paused"
    STATUS_BREAK = "on_break"
    STATUS_POMODORO = "pomodoro"

    def __init__(self, opacity: float = 0.95, position: str = "top-right", pomodoro_enabled: bool = True):
        super().__init__()
        self._drag_position: Optional[QPoint] = None
        self._position = position
        self._paused = False
        self._on_break = False
        self._pomodoro_enabled = pomodoro_enabled
        self._pomodoro_running = False
        self._setup_ui()
        self.setWindowOpacity(opacity)
        self.set_status(self.STATUS_GOOD, {})

        # Clock update timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)  # Update every second
        self._update_clock()

    def _setup_ui(self) -> None:
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, True)
        self.setAttribute(Qt.WidgetAttribute.WA_MacAlwaysShowToolWindow, True)

        # Main layout
        layout = QHBoxLayout()
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(14)

        # System clock on the left
        self.clock_label = QLabel("00:00")
        font = QFont("SF Mono, Menlo, Monaco, monospace")
        font.setPointSize(18)
        font.setBold(True)
        self.clock_label.setFont(font)
        self.clock_label.setStyleSheet("color: #e5e5e5; background: transparent;")
        layout.addWidget(self.clock_label)

        # Separator line
        separator = QLabel()
        separator.setFixedSize(1, 32)
        separator.setStyleSheet("background-color: #333333;")
        layout.addWidget(separator)

        # Arc progress
        self.arc_progress = ArcProgress()
        layout.addWidget(self.arc_progress)

        # Info section
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)

        # Time/status label (pomodoro time)
        self.time_label = QLabel("25:00")
        font = QFont("SF Mono, Menlo, Monaco, monospace")
        font.setPointSize(14)
        font.setBold(True)
        self.time_label.setFont(font)
        info_layout.addWidget(self.time_label)

        # Sub label
        self.status_label = QLabel("Ready")
        font = QFont()
        font.setPointSize(9)
        self.status_label.setFont(font)
        info_layout.addWidget(self.status_label)

        layout.addLayout(info_layout)

        # Pomodoro count indicator
        self.count_label = QLabel("")
        font = QFont("SF Mono, Menlo, Monaco, monospace")
        font.setPointSize(11)
        self.count_label.setFont(font)
        self.count_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(self.count_label)

        self.setLayout(layout)
        self.setFixedHeight(56)
        self.setMinimumWidth(240)

        self._position_widget()

    def _position_widget(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            margin = 20

            if self._position == "top-right":
                x = geometry.right() - self.width() - margin
                y = geometry.top() + margin
            elif self._position == "top-left":
                x = geometry.left() + margin
                y = geometry.top() + margin
            elif self._position == "bottom-right":
                x = geometry.right() - self.width() - margin
                y = geometry.bottom() - self.height() - margin - 60
            else:
                x = geometry.left() + margin
                y = geometry.bottom() - self.height() - margin

            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 40)))
        painter.drawRoundedRect(2, 2, self.width() - 2, self.height() - 2, 14, 14)

        # Background
        painter.setBrush(QBrush(QColor("#0a0a0a")))
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 14, 14)

        # Subtle border
        painter.setPen(QPen(QColor(35, 35, 35), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 14, 14)

    def _update_clock(self) -> None:
        """Update the system clock display."""
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M"))

    def set_status(self, status: str, data: Dict[str, Any]) -> None:
        pomodoro_state = data.get("pomodoro_state", "idle")
        remaining_secs = data.get("remaining_seconds", 0)
        pomodoro_count = data.get("pomodoro_count", 0)
        session_mins = data.get("session_minutes", 0)

        # Determine display values
        if self._pomodoro_enabled and pomodoro_state in ("working", "short_break", "long_break"):
            mins = remaining_secs // 60
            secs = remaining_secs % 60
            time_text = f"{mins:02d}:{secs:02d}"

            if pomodoro_state == "working":
                total_secs = 25 * 60
                progress = int(((total_secs - remaining_secs) / total_secs) * 100)
            else:
                total_secs = 5 * 60 if pomodoro_state == "short_break" else 15 * 60
                progress = int(((total_secs - remaining_secs) / total_secs) * 100)
        else:
            hours = session_mins // 60
            mins = session_mins % 60
            time_text = f"{hours}h {mins:02d}m" if hours > 0 else f"{mins}m"
            progress = 0

        self.time_label.setText(time_text)

        # Pomodoro count
        if pomodoro_count > 0:
            self.count_label.setText(f"#{pomodoro_count}")
            self.count_label.show()
        else:
            self.count_label.hide()

        # Set colors and status based on state
        if self._on_break or pomodoro_state in ("short_break", "long_break"):
            status_text = "Break" if pomodoro_state == "short_break" else "Long break"
            color = "#22d3ee"  # Cyan
            self._pomodoro_running = False

        elif self._paused or pomodoro_state == "paused":
            status_text = "Paused"
            color = "#6b7280"
            progress = 0
            self._pomodoro_running = False

        elif pomodoro_state == "working":
            self._pomodoro_running = True
            status_text = "Focus"
            color = "#22c55e"  # Green

        elif status == self.STATUS_OVERTIME:
            status_text = "Overtime"
            color = "#ef4444"  # Red
            progress = 100

        elif status == self.STATUS_NEEDS_BREAK:
            status_text = "Break time?"
            color = "#f59e0b"  # Amber
            progress = 100

        else:
            self._pomodoro_running = False
            status_text = "Ready" if pomodoro_count == 0 else f"{pomodoro_count} done"
            color = "#6b7280"

        self.status_label.setText(status_text)
        self.arc_progress.set_progress(progress, color, pomodoro_state == "working")

        # Text colors
        self.time_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.status_label.setStyleSheet("color: #6b7280; background: transparent;")
        self.count_label.setStyleSheet(f"color: {color}; background: transparent;")

        self.adjustSize()

    def update_pomodoro_tick(self, remaining_seconds: int, pomodoro_count: int, state: str) -> None:
        mins = remaining_seconds // 60
        secs = remaining_seconds % 60
        self.time_label.setText(f"{mins:02d}:{secs:02d}")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #0a0a0a;
                color: #e5e5e5;
                border: 1px solid #262626;
                border-radius: 8px;
                padding: 4px;
            }
            QMenu::item {
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #262626;
            }
            QMenu::separator {
                height: 1px;
                background: #262626;
                margin: 4px 8px;
            }
        """)

        if self._pomodoro_enabled:
            if self._pomodoro_running:
                stop_action = QAction("Stop Focus", self)
                stop_action.triggered.connect(self.pomodoro_stop.emit)
                menu.addAction(stop_action)
            else:
                start_action = QAction("Start Focus", self)
                start_action.triggered.connect(self.pomodoro_start.emit)
                menu.addAction(start_action)

            menu.addSeparator()

        break_action = QAction("Take Break", self)
        break_action.triggered.connect(self.break_requested.emit)
        menu.addAction(break_action)

        stats_action = QAction("View Stats", self)
        stats_action.triggered.connect(self.stats_requested.emit)
        menu.addAction(stats_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        if self._paused:
            pause_action = QAction("Resume", self)
            pause_action.triggered.connect(lambda: self._toggle_pause(False))
        else:
            pause_action = QAction("Pause", self)
            pause_action.triggered.connect(lambda: self._toggle_pause(True))
        menu.addAction(pause_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def _toggle_pause(self, paused: bool) -> None:
        self._paused = paused
        self.pause_requested.emit(paused)
        self.set_status(self.STATUS_PAUSED if paused else self.STATUS_GOOD, {})

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if event.buttons() == Qt.MouseButton.LeftButton and self._drag_position:
            self.move(event.globalPosition().toPoint() - self._drag_position)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self._drag_position = None

    def mouseDoubleClickEvent(self, event) -> None:
        if self._pomodoro_enabled:
            if self._pomodoro_running:
                self.pomodoro_stop.emit()
            else:
                self.pomodoro_start.emit()
