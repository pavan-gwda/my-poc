"""Friendly assistant widget UI for Voice Commander."""

import math
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QVBoxLayout,
    QHBoxLayout,
    QMenu,
    QApplication,
    QGraphicsDropShadowEffect,
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import QFont, QAction, QPainter, QColor, QBrush, QPen
from typing import Optional


class PulsingOrb(QWidget):
    """Animated pulsing orb that represents the assistant."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(60, 60)
        self._pulse_phase = 0
        self._is_active = False
        self._base_color = QColor("#6b7280")  # Gray when idle
        self._glow_intensity = 0

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._animate)
        self._timer.start(30)  # ~33 FPS

    def set_state(self, state: str):
        """Set the orb state and color."""
        colors = {
            "idle": "#6b7280",      # Gray
            "listening": "#22c55e", # Green
            "processing": "#3b82f6", # Blue
            "executing": "#f59e0b", # Amber
            "success": "#22c55e",   # Green
            "error": "#ef4444",     # Red
        }
        self._base_color = QColor(colors.get(state, "#6b7280"))
        self._is_active = state in ("listening", "processing", "executing")
        self.update()

    def _animate(self):
        self._pulse_phase += 0.1
        if self._is_active:
            self._glow_intensity = (math.sin(self._pulse_phase * 2) + 1) / 2 * 0.5 + 0.5
        else:
            self._glow_intensity = max(0, self._glow_intensity - 0.05)
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        center_x = self.width() // 2
        center_y = self.height() // 2
        base_radius = 22

        # Outer glow when active
        if self._glow_intensity > 0:
            for i in range(3):
                glow_radius = base_radius + 8 + i * 4
                alpha = int(60 * self._glow_intensity * (1 - i * 0.3))
                glow_color = QColor(self._base_color)
                glow_color.setAlpha(alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(glow_color))
                painter.drawEllipse(
                    center_x - glow_radius,
                    center_y - glow_radius,
                    glow_radius * 2,
                    glow_radius * 2
                )

        # Main orb with gradient effect
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(self._base_color))
        painter.drawEllipse(
            center_x - base_radius,
            center_y - base_radius,
            base_radius * 2,
            base_radius * 2
        )

        # Inner highlight
        highlight_color = QColor(255, 255, 255, 80)
        painter.setBrush(QBrush(highlight_color))
        painter.drawEllipse(
            center_x - base_radius + 6,
            center_y - base_radius + 4,
            12, 10
        )

        # Sound wave lines when listening
        if self._is_active and self._glow_intensity > 0.3:
            painter.setPen(QPen(QColor(255, 255, 255, int(150 * self._glow_intensity)), 2))
            for i in range(3):
                wave_offset = math.sin(self._pulse_phase * 3 + i * 1.5) * 4
                y_pos = center_y - 6 + i * 6
                painter.drawLine(
                    int(center_x - 8 + wave_offset),
                    int(y_pos),
                    int(center_x + 8 + wave_offset),
                    int(y_pos)
                )


class FloatingWidget(QWidget):
    """Friendly assistant widget for voice commander."""

    mode_changed = pyqtSignal(str)
    quit_requested = pyqtSignal()

    STATUS_IDLE = "idle"
    STATUS_LISTENING = "listening"
    STATUS_PROCESSING = "processing"
    STATUS_EXECUTING = "executing"
    STATUS_SUCCESS = "success"
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
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(15, 15, 15, 15)
        main_layout.setSpacing(8)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # Pulsing orb
        self.orb = PulsingOrb()
        main_layout.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignCenter)

        # Status text
        self.status_label = QLabel("Hi there!")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(11)
        font.setBold(True)
        self.status_label.setFont(font)
        main_layout.addWidget(self.status_label)

        # Hint text
        self.hint_label = QLabel("Hold Option to speak")
        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(9)
        self.hint_label.setFont(font)
        main_layout.addWidget(self.hint_label)

        self.setLayout(main_layout)
        self.setFixedSize(140, 130)

        self._position_widget()

    def _position_widget(self) -> None:
        screen = QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            x = geometry.right() - self.width() - 20
            y = geometry.top() + 80
            self.move(x, y)

    def paintEvent(self, event):
        """Draw rounded background."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Shadow
        shadow_color = QColor(0, 0, 0, 40)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(shadow_color))
        painter.drawRoundedRect(4, 4, self.width() - 4, self.height() - 4, 20, 20)

        # Background
        bg_color = QColor("#1a1a2e")
        painter.setBrush(QBrush(bg_color))
        painter.drawRoundedRect(0, 0, self.width() - 4, self.height() - 4, 20, 20)

    def set_status(self, status: str, message: str = "", command: str = "") -> None:
        self._current_status = status
        self.orb.set_state(status)

        messages = {
            self.STATUS_IDLE: ("Hi there!", "Hold Option to speak"),
            self.STATUS_LISTENING: ("I'm listening...", "Speak your command"),
            self.STATUS_PROCESSING: ("Thinking...", "Processing your request"),
            self.STATUS_EXECUTING: (message or "On it!", "Executing command"),
            self.STATUS_SUCCESS: (message or "Done!", ""),
            self.STATUS_ERROR: (message or "Oops!", "Try again"),
        }

        text, hint = messages.get(status, ("Hi!", ""))

        # Show command if provided
        if command:
            hint = f'"{command}"'

        self.status_label.setText(text)
        self.hint_label.setText(hint)
        self.hint_label.setVisible(bool(hint))

        # Text colors
        colors = {
            self.STATUS_IDLE: "#9ca3af",
            self.STATUS_LISTENING: "#86efac",
            self.STATUS_PROCESSING: "#93c5fd",
            self.STATUS_EXECUTING: "#fcd34d",
            self.STATUS_SUCCESS: "#86efac",
            self.STATUS_ERROR: "#fca5a5",
        }

        color = colors.get(status, "#9ca3af")
        self.status_label.setStyleSheet(f"color: {color}; background: transparent;")
        self.hint_label.setStyleSheet("color: #6b7280; background: transparent;")

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        menu.setStyleSheet("""
            QMenu {
                background-color: #1a1a2e;
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

        # Mode selection
        mode_menu = menu.addMenu("Activation Mode")

        hold_action = QAction("Hold to Command", self)
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
