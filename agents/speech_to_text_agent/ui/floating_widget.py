"""Floating tray widget UI for Speech-to-Text."""

import math
import random
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QHBoxLayout,
    QMenu,
    QApplication,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont, QAction, QPainter, QColor, QBrush, QPen, QLinearGradient
from typing import Optional


class WaveVisualizer(QWidget):
    """Animated wave visualizer for recording state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 32)
        self._bars = [0.3] * 12
        self._target_bars = [0.3] * 12
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
        self._bars = [0.3] * 12
        self.update()

    def _animate(self):
        self._frame += 1
        for i in range(12):
            wave = math.sin(self._frame * 0.2 + i * 0.5) * 0.35 + 0.5
            noise = random.uniform(-0.08, 0.08)
            self._target_bars[i] = max(0.15, min(1.0, wave + noise))
        for i in range(12):
            diff = self._target_bars[i] - self._bars[i]
            self._bars[i] += diff * 0.25
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        bar_width = 4
        gap = 6
        total_width = 12 * bar_width + 11 * gap
        start_x = (self.width() - total_width) // 2
        max_height = self.height() - 6

        for i, height_ratio in enumerate(self._bars):
            x = start_x + i * (bar_width + gap)
            bar_height = int(max_height * height_ratio)
            y = (self.height() - bar_height) // 2

            # White bars
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QBrush(QColor(255, 255, 255, 230)))
            painter.drawRoundedRect(x, y, bar_width, bar_height, 2, 2)


class ProgressBar(QWidget):
    """Animated progress bar for processing state."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(120, 6)
        self._progress = 0
        self._shimmer_pos = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)

    def start(self):
        self._progress = 0
        self._shimmer_pos = 0
        self._timer.start(30)

    def stop(self):
        self._timer.stop()
        self._progress = 0
        self.update()

    def _animate(self):
        self._shimmer_pos = (self._shimmer_pos + 3) % (self.width() + 40)
        self._progress = min(95, self._progress + 0.5)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Background track
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(60, 60, 60)))
        painter.drawRoundedRect(0, 0, self.width(), self.height(), 3, 3)

        # Progress fill
        if self._progress > 0:
            progress_width = int(self.width() * self._progress / 100)

            # Gradient fill
            gradient = QLinearGradient(0, 0, progress_width, 0)
            gradient.setColorAt(0, QColor("#3b82f6"))
            gradient.setColorAt(1, QColor("#60a5fa"))
            painter.setBrush(QBrush(gradient))
            painter.drawRoundedRect(0, 0, progress_width, self.height(), 3, 3)

            # Shimmer effect
            shimmer_width = 30
            if self._shimmer_pos < progress_width:
                shimmer_gradient = QLinearGradient(self._shimmer_pos - shimmer_width, 0, self._shimmer_pos, 0)
                shimmer_gradient.setColorAt(0, QColor(255, 255, 255, 0))
                shimmer_gradient.setColorAt(0.5, QColor(255, 255, 255, 80))
                shimmer_gradient.setColorAt(1, QColor(255, 255, 255, 0))
                painter.setBrush(QBrush(shimmer_gradient))
                painter.drawRoundedRect(0, 0, min(self._shimmer_pos, progress_width), self.height(), 3, 3)


class FloatingWidget(QWidget):
    """Floating tray widget for speech-to-text status."""

    mode_changed = pyqtSignal(str)
    quit_requested = pyqtSignal()

    STATUS_IDLE = "idle"
    STATUS_RECORDING = "recording"
    STATUS_PROCESSING = "processing"
    STATUS_DONE = "done"
    STATUS_ERROR = "error"

    def __init__(self, opacity: float = 0.95, activation_mode: str = "hold"):
        super().__init__()
        self.activation_mode = activation_mode
        self._drag_position: Optional[QPoint] = None
        self._current_status = self.STATUS_IDLE
        self._setup_ui()
        self.setWindowOpacity(opacity)
        self.set_status(self.STATUS_IDLE)

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
        layout.setContentsMargins(16, 10, 16, 10)
        layout.setSpacing(12)

        # Status indicator dot
        self.status_dot = QLabel()
        self.status_dot.setFixedSize(8, 8)
        layout.addWidget(self.status_dot)

        # Status text (shown when idle)
        self.status_label = QLabel("Ready")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(12)
        self.status_label.setFont(font)
        layout.addWidget(self.status_label)

        # Wave visualizer (shown when recording)
        self.wave_visualizer = WaveVisualizer()
        self.wave_visualizer.hide()
        layout.addWidget(self.wave_visualizer)

        # Progress bar (shown when processing)
        self.progress_bar = ProgressBar()
        self.progress_bar.hide()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)
        self.setFixedHeight(44)
        self.setMinimumWidth(160)

        self._position_widget()

    def _position_widget(self) -> None:
        """Position at bottom center of screen."""
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = (geometry.width() - self.width()) // 2
            y = geometry.bottom() - self.height() - 30
            self.move(x, y)

    def paintEvent(self, event):
        """Draw rounded pill background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow
        shadow_color = QColor(0, 0, 0, 50)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRoundedRect(2, 2, self.width() - 2, self.height() - 2, 22, 22)

        # Background - dark pill shape
        bg_color = QColor("#0a0a0a")
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 22, 22)

        # Subtle border
        painter.setPen(QPen(QColor(40, 40, 40), 1))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawRoundedRect(0, 0, self.width() - 2, self.height() - 2, 22, 22)

    def set_status(self, status: str, message: str = "") -> None:
        self._current_status = status

        # Hide all visualizers first
        self.wave_visualizer.hide()
        self.wave_visualizer.stop()
        self.progress_bar.hide()
        self.progress_bar.stop()
        self.status_label.hide()

        if status == self.STATUS_IDLE:
            self.status_label.setText("Ready")
            self.status_label.setStyleSheet("color: #6b7280; background: transparent;")
            self.status_label.show()
            self._set_dot_color("#6b7280")
            self.setFixedWidth(160)

        elif status == self.STATUS_RECORDING:
            self.wave_visualizer.show()
            self.wave_visualizer.start()
            self._set_dot_color("#22c55e")
            self.setFixedWidth(180)

        elif status == self.STATUS_PROCESSING:
            self.progress_bar.show()
            self.progress_bar.start()
            self._set_dot_color("#3b82f6")
            self.setFixedWidth(180)

        elif status == self.STATUS_DONE:
            self.status_label.setText(message or "Done!")
            self.status_label.setStyleSheet("color: #22c55e; background: transparent;")
            self.status_label.show()
            self._set_dot_color("#22c55e")
            self.setFixedWidth(160)

        elif status == self.STATUS_ERROR:
            self.status_label.setText(message or "Error")
            self.status_label.setStyleSheet("color: #ef4444; background: transparent;")
            self.status_label.show()
            self._set_dot_color("#ef4444")
            self.setFixedWidth(160)

        self.adjustSize()
        self._position_widget()

    def _set_dot_color(self, color: str):
        self.status_dot.setStyleSheet(f"""
            background-color: {color};
            border-radius: 4px;
        """)

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a1a;
                color: white;
                border: 1px solid #333;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 20px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background-color: #333;
            }
        """)

        mode_menu = menu.addMenu("Activation Mode")

        hold_action = QAction("Hold to Record", self)
        hold_action.setCheckable(True)
        hold_action.setChecked(self.activation_mode == "hold")
        hold_action.triggered.connect(lambda: self._set_mode("hold"))
        mode_menu.addAction(hold_action)

        toggle_action = QAction("Toggle Recording", self)
        toggle_action.setCheckable(True)
        toggle_action.setChecked(self.activation_mode == "toggle")
        toggle_action.triggered.connect(lambda: self._set_mode("toggle"))
        mode_menu.addAction(toggle_action)

        menu.addSeparator()

        quit_action = QAction("Quit", self)
        quit_action.triggered.connect(self.quit_requested.emit)
        menu.addAction(quit_action)

        menu.exec(event.globalPos())

    def _set_mode(self, mode: str) -> None:
        self.activation_mode = mode
        self.mode_changed.emit(mode)

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
