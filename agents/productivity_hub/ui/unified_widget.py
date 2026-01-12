"""Unified Productivity Hub Widget - combines all agents in one UI."""

import math
import random
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
from PyQt6.QtGui import QFont, QAction, QPainter, QColor, QBrush, QPen, QLinearGradient
from typing import Optional, Dict, Any


class MiniArcProgress(QWidget):
    """Small arc progress for pomodoro."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(36, 36)
        self._progress = 0
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
        radius = 14
        thickness = 2.5

        painter.setPen(QPen(QColor(40, 40, 40), thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawArc(center - radius, center - radius, radius * 2, radius * 2, 0, 360 * 16)

        if self._progress > 0:
            color = QColor(self._color)
            if self._is_active:
                alpha = int(200 + 55 * math.sin(self._pulse_phase * 2))
                color.setAlpha(alpha)

            painter.setPen(QPen(color, thickness, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            span = int(self._progress * 3.6 * 16)
            painter.drawArc(center - radius, center - radius, radius * 2, radius * 2, 90 * 16, -span)


class MiniWaveVisualizer(QWidget):
    """Small wave visualizer for STT."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 20)
        self._bars = [0.3] * 5
        self._target_bars = [0.3] * 5
        self._is_active = False
        self._frame = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        self._is_active = True
        self._timer.start(40)

    def stop(self):
        self._is_active = False
        self._timer.stop()
        self._bars = [0.3] * 5
        self.update()

    def _animate(self):
        self._frame += 1
        for i in range(5):
            wave = math.sin(self._frame * 0.2 + i * 0.5) * 0.35 + 0.5
            noise = random.uniform(-0.08, 0.08)
            self._target_bars[i] = max(0.15, min(1.0, wave + noise))
        for i in range(5):
            diff = self._target_bars[i] - self._bars[i]
            self._bars[i] += diff * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 3
        gap = 4
        total_width = 5 * bar_width + 4 * gap
        start_x = (self.width() - total_width) // 2
        max_height = self.height() - 4

        for i, height_ratio in enumerate(self._bars):
            x = start_x + i * (bar_width + gap)
            bar_height = int(max_height * height_ratio)
            y = (self.height() - bar_height) // 2

            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.drawRoundedRect(x, y, bar_width, bar_height, 1, 1)


class StatusDot(QWidget):
    """Animated status dot."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._color = QColor("#6b7280")
        self._is_active = False
        self._pulse_phase = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(50)

    def set_state(self, color: str, active: bool = False):
        self._color = QColor(color)
        self._is_active = active
        self.update()

    def _animate(self):
        self._pulse_phase += 0.15
        if self._is_active:
            self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center = self.width() // 2

        if self._is_active:
            glow_alpha = int(60 + 40 * math.sin(self._pulse_phase * 2))
            glow_color = QColor(self._color)
            glow_color.setAlpha(glow_alpha)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(glow_color))
            painter.drawEllipse(0, 0, 12, 12)

        painter.setBrush(QBrush(self._color))
        painter.drawEllipse(2, 2, 8, 8)


class UnifiedWidget(QWidget):
    """Unified productivity hub widget."""

    # Burnout signals
    break_requested = pyqtSignal()
    stats_requested = pyqtSignal()
    settings_requested = pyqtSignal()
    quit_requested = pyqtSignal()
    restart_requested = pyqtSignal()
    pause_requested = pyqtSignal(bool)
    pomodoro_start = pyqtSignal()
    pomodoro_stop = pyqtSignal()

    # STT/VC mode signals
    stt_mode_changed = pyqtSignal(str)
    vc_mode_changed = pyqtSignal(str)

    # Module restart signals
    stt_restart_requested = pyqtSignal()
    vc_restart_requested = pyqtSignal()
    hotkeys_restart_requested = pyqtSignal()

    # Sleep/Wake signal
    sleep_requested = pyqtSignal(bool)  # True = sleep, False = wake

    def __init__(self, opacity: float = 0.95, position: str = "top-right"):
        super().__init__()
        self._drag_position: Optional[QPoint] = None
        self._position = position
        self._paused = False
        self._pomodoro_running = False
        self._sleeping = False  # Sleep mode state

        # STT state
        self._stt_status = "idle"
        self._stt_mode = "hold"

        # VC state
        self._vc_status = "idle"
        self._vc_mode = "hold"

        self._setup_ui()
        self.setWindowOpacity(opacity)

        # Clock timer
        self._clock_timer = QTimer(self)
        self._clock_timer.timeout.connect(self._update_clock)
        self._clock_timer.start(1000)
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
        layout.setContentsMargins(14, 8, 14, 8)
        layout.setSpacing(12)

        # === Clock Section ===
        self.clock_label = QLabel("00:00")
        font = QFont("SF Mono, Menlo, Monaco, monospace")
        font.setPointSize(20)
        font.setBold(True)
        self.clock_label.setFont(font)
        self.clock_label.setStyleSheet("color: #e5e5e5; background: transparent;")
        layout.addWidget(self.clock_label)

        self._add_separator(layout)

        # === Pomodoro Section ===
        pomodoro_layout = QHBoxLayout()
        pomodoro_layout.setSpacing(6)

        self.arc_progress = MiniArcProgress()
        pomodoro_layout.addWidget(self.arc_progress)

        pomo_info = QVBoxLayout()
        pomo_info.setSpacing(0)

        self.pomo_time_label = QLabel("25:00")
        font = QFont("SF Mono, Menlo, Monaco, monospace")
        font.setPointSize(12)
        font.setBold(True)
        self.pomo_time_label.setFont(font)
        self.pomo_time_label.setStyleSheet("color: #6b7280; background: transparent;")
        pomo_info.addWidget(self.pomo_time_label)

        self.pomo_status_label = QLabel("Ready")
        font = QFont()
        font.setPointSize(8)
        self.pomo_status_label.setFont(font)
        self.pomo_status_label.setStyleSheet("color: #4b5563; background: transparent;")
        pomo_info.addWidget(self.pomo_status_label)

        pomodoro_layout.addLayout(pomo_info)
        layout.addLayout(pomodoro_layout)

        self._add_separator(layout)

        # === Speech-to-Text Section ===
        stt_layout = QVBoxLayout()
        stt_layout.setSpacing(2)

        stt_header = QHBoxLayout()
        stt_header.setSpacing(4)

        self.stt_dot = StatusDot()
        stt_header.addWidget(self.stt_dot)

        stt_label = QLabel("STT")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        stt_label.setFont(font)
        stt_label.setStyleSheet("color: #9ca3af; background: transparent;")
        stt_header.addWidget(stt_label)

        stt_layout.addLayout(stt_header)

        self.stt_wave = MiniWaveVisualizer()
        self.stt_wave.hide()
        stt_layout.addWidget(self.stt_wave)

        self.stt_status_label = QLabel("Ready")
        font = QFont()
        font.setPointSize(8)
        self.stt_status_label.setFont(font)
        self.stt_status_label.setStyleSheet("color: #4b5563; background: transparent;")
        stt_layout.addWidget(self.stt_status_label)

        layout.addLayout(stt_layout)

        self._add_separator(layout)

        # === Voice Commander Section ===
        vc_layout = QVBoxLayout()
        vc_layout.setSpacing(2)

        vc_header = QHBoxLayout()
        vc_header.setSpacing(4)

        self.vc_dot = StatusDot()
        vc_header.addWidget(self.vc_dot)

        vc_label = QLabel("CMD")
        font = QFont()
        font.setPointSize(9)
        font.setBold(True)
        vc_label.setFont(font)
        vc_label.setStyleSheet("color: #9ca3af; background: transparent;")
        vc_header.addWidget(vc_label)

        vc_layout.addLayout(vc_header)

        self.vc_status_label = QLabel("Ready")
        font = QFont()
        font.setPointSize(8)
        self.vc_status_label.setFont(font)
        self.vc_status_label.setStyleSheet("color: #4b5563; background: transparent;")
        vc_layout.addWidget(self.vc_status_label)

        layout.addLayout(vc_layout)

        self.setLayout(layout)
        self.setFixedHeight(52)
        self.setMinimumWidth(380)

        self._position_widget()

    def _add_separator(self, layout):
        sep = QLabel()
        sep.setFixedSize(1, 32)
        sep.setStyleSheet("background-color: #333333;")
        layout.addWidget(sep)

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
            elif self._position == "top-center":
                x = (geometry.width() - self.width()) // 2
                y = geometry.top() + margin
            else:
                x = geometry.right() - self.width() - margin
                y = geometry.top() + margin

            self.move(x, y)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(0, 0, 0, 50)))
        painter.drawRoundedRect(2, 2, self.width() - 2, self.height() - 2, 16, 16)

        # Background
        painter.setBrush(QBrush(QColor("#0a0a0a")))
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 16, 16)

        # Border
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 16, 16)

    def _update_clock(self) -> None:
        now = datetime.now()
        self.clock_label.setText(now.strftime("%H:%M"))

    # === Pomodoro/Burnout Methods ===
    def set_pomodoro_status(self, status: str, data: Dict[str, Any]) -> None:
        pomodoro_state = data.get("pomodoro_state", "idle")
        remaining_secs = data.get("remaining_seconds", 0)
        session_mins = data.get("session_minutes", 0)

        if pomodoro_state in ("working", "short_break", "long_break"):
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

        self.pomo_time_label.setText(time_text)

        if pomodoro_state in ("short_break", "long_break"):
            status_text = "Break"
            color = "#22d3ee"
            self._pomodoro_running = False
        elif self._paused or pomodoro_state == "paused":
            status_text = "Paused"
            color = "#6b7280"
            progress = 0
            self._pomodoro_running = False
        elif pomodoro_state == "working":
            self._pomodoro_running = True
            status_text = "Focus"
            color = "#22c55e"
        elif status == "overtime":
            status_text = "Overtime"
            color = "#ef4444"
            progress = 100
        elif status == "needs_break":
            status_text = "Break?"
            color = "#f59e0b"
            progress = 100
        else:
            self._pomodoro_running = False
            status_text = "Ready"
            color = "#6b7280"

        self.pomo_status_label.setText(status_text)
        self.pomo_time_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.arc_progress.set_progress(progress, color, pomodoro_state == "working")

    # === STT Methods ===
    def set_stt_status(self, status: str, message: str = "") -> None:
        self._stt_status = status

        if status == "idle":
            self.stt_dot.set_state("#6b7280", False)
            self.stt_status_label.setText("Ready")
            self.stt_wave.hide()
            self.stt_wave.stop()
            self.stt_status_label.show()

        elif status == "recording":
            self.stt_dot.set_state("#22c55e", True)
            self.stt_status_label.hide()
            self.stt_wave.show()
            self.stt_wave.start()

        elif status == "processing":
            self.stt_dot.set_state("#3b82f6", True)
            self.stt_wave.hide()
            self.stt_wave.stop()
            self.stt_status_label.setText("...")
            self.stt_status_label.show()

        elif status == "done":
            self.stt_dot.set_state("#22c55e", False)
            self.stt_wave.hide()
            self.stt_wave.stop()
            self.stt_status_label.setText("Done")
            self.stt_status_label.show()

        elif status == "error":
            self.stt_dot.set_state("#ef4444", False)
            self.stt_wave.hide()
            self.stt_wave.stop()
            self.stt_status_label.setText("Error")
            self.stt_status_label.show()

    # === Voice Commander Methods ===
    def set_vc_status(self, status: str, message: str = "") -> None:
        self._vc_status = status

        colors = {
            "idle": ("#6b7280", False),
            "listening": ("#22c55e", True),
            "processing": ("#3b82f6", True),
            "executing": ("#f59e0b", True),
            "success": ("#22c55e", False),
            "error": ("#ef4444", False),
        }

        labels = {
            "idle": "Ready",
            "listening": "Listening",
            "processing": "Thinking",
            "executing": "Running",
            "success": "Done",
            "error": "Error",
        }

        color, active = colors.get(status, ("#6b7280", False))
        self.vc_dot.set_state(color, active)
        self.vc_status_label.setText(message or labels.get(status, "Ready"))

    # === Context Menu ===
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

        # Pomodoro actions
        pomo_menu = menu.addMenu("Pomodoro")
        if self._pomodoro_running:
            stop_action = QAction("Stop Focus", self)
            stop_action.triggered.connect(self.pomodoro_stop.emit)
            pomo_menu.addAction(stop_action)
        else:
            start_action = QAction("Start Focus", self)
            start_action.triggered.connect(self.pomodoro_start.emit)
            pomo_menu.addAction(start_action)

        break_action = QAction("Take Break", self)
        break_action.triggered.connect(self.break_requested.emit)
        pomo_menu.addAction(break_action)

        menu.addSeparator()

        # STT mode
        stt_menu = menu.addMenu("STT Mode")
        hold_stt = QAction("Hold to Record", self)
        hold_stt.setCheckable(True)
        hold_stt.setChecked(self._stt_mode == "hold")
        hold_stt.triggered.connect(lambda: self._set_stt_mode("hold"))
        stt_menu.addAction(hold_stt)

        toggle_stt = QAction("Toggle Recording", self)
        toggle_stt.setCheckable(True)
        toggle_stt.setChecked(self._stt_mode == "toggle")
        toggle_stt.triggered.connect(lambda: self._set_stt_mode("toggle"))
        stt_menu.addAction(toggle_stt)

        # VC mode
        vc_menu = menu.addMenu("Command Mode")
        hold_vc = QAction("Hold to Command", self)
        hold_vc.setCheckable(True)
        hold_vc.setChecked(self._vc_mode == "hold")
        hold_vc.triggered.connect(lambda: self._set_vc_mode("hold"))
        vc_menu.addAction(hold_vc)

        toggle_vc = QAction("Toggle Recording", self)
        toggle_vc.setCheckable(True)
        toggle_vc.setChecked(self._vc_mode == "toggle")
        toggle_vc.triggered.connect(lambda: self._set_vc_mode("toggle"))
        vc_menu.addAction(toggle_vc)

        menu.addSeparator()

        stats_action = QAction("View Stats", self)
        stats_action.triggered.connect(self.stats_requested.emit)
        menu.addAction(stats_action)

        settings_action = QAction("Settings", self)
        settings_action.triggered.connect(self.settings_requested.emit)
        menu.addAction(settings_action)

        menu.addSeparator()

        # Sleep/Wake option
        if self._sleeping:
            sleep_action = QAction("☀ Wake Up", self)
            sleep_action.triggered.connect(lambda: self._toggle_sleep(False))
        else:
            sleep_action = QAction("😴 Sleep", self)
            sleep_action.triggered.connect(lambda: self._toggle_sleep(True))
        menu.addAction(sleep_action)

        if self._paused:
            pause_action = QAction("Resume Tracking", self)
            pause_action.triggered.connect(lambda: self._toggle_pause(False))
        else:
            pause_action = QAction("Pause Tracking", self)
            pause_action.triggered.connect(lambda: self._toggle_pause(True))
        menu.addAction(pause_action)

        menu.addSeparator()

        # Troubleshooting submenu
        troubleshoot_menu = menu.addMenu("Troubleshoot")

        restart_stt_action = QAction("Restart STT Module", self)
        restart_stt_action.triggered.connect(self.stt_restart_requested.emit)
        troubleshoot_menu.addAction(restart_stt_action)

        restart_vc_action = QAction("Restart VC Module", self)
        restart_vc_action.triggered.connect(self.vc_restart_requested.emit)
        troubleshoot_menu.addAction(restart_vc_action)

        restart_hotkeys_action = QAction("Restart Hotkeys", self)
        restart_hotkeys_action.triggered.connect(self.hotkeys_restart_requested.emit)
        troubleshoot_menu.addAction(restart_hotkeys_action)

        troubleshoot_menu.addSeparator()

        restart_all_action = QAction("Restart All Modules", self)
        restart_all_action.triggered.connect(self._restart_all_modules)
        troubleshoot_menu.addAction(restart_all_action)

        menu.addSeparator()

        restart_action = QAction("Restart App", self)
        restart_action.triggered.connect(self.restart_requested.emit)
        menu.addAction(restart_action)

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def _set_stt_mode(self, mode: str) -> None:
        self._stt_mode = mode
        self.stt_mode_changed.emit(mode)

    def _set_vc_mode(self, mode: str) -> None:
        self._vc_mode = mode
        self.vc_mode_changed.emit(mode)

    def _toggle_pause(self, paused: bool) -> None:
        self._paused = paused
        self.pause_requested.emit(paused)

    def _restart_all_modules(self) -> None:
        """Restart all modules (STT, VC, Hotkeys)."""
        self.stt_restart_requested.emit()
        self.vc_restart_requested.emit()
        self.hotkeys_restart_requested.emit()

    def _toggle_sleep(self, sleeping: bool) -> None:
        """Toggle sleep mode."""
        self._sleeping = sleeping
        self.sleep_requested.emit(sleeping)
        self._update_sleep_ui()

    def set_sleep_mode(self, sleeping: bool) -> None:
        """Set sleep mode from external source."""
        self._sleeping = sleeping
        self._update_sleep_ui()

    def _update_sleep_ui(self) -> None:
        """Update UI to reflect sleep state."""
        if self._sleeping:
            # Dim everything when sleeping
            self.setWindowOpacity(0.6)
            self.clock_label.setStyleSheet("color: #4b5563; background: transparent;")
            self.pomo_time_label.setStyleSheet("color: #4b5563; background: transparent;")
            self.pomo_status_label.setText("Sleeping")
            self.stt_status_label.setText("Sleeping")
            self.vc_status_label.setText("Sleeping")
            self.stt_dot.set_state("#374151", False)
            self.vc_dot.set_state("#374151", False)
            self.arc_progress.set_progress(0, "#374151", False)
        else:
            # Restore normal appearance
            self.setWindowOpacity(0.95)
            self.clock_label.setStyleSheet("color: #e5e5e5; background: transparent;")
            self.pomo_status_label.setText("Ready")
            self.stt_status_label.setText("Ready")
            self.vc_status_label.setText("Ready")
            self.stt_dot.set_state("#6b7280", False)
            self.vc_dot.set_state("#6b7280", False)

    # === Drag support ===
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
        if self._pomodoro_running:
            self.pomodoro_stop.emit()
        else:
            self.pomodoro_start.emit()
