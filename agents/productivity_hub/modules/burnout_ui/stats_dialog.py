"""Statistics dialog for viewing activity data."""

from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGridLayout,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from typing import Dict, Any, List


class StatsDialog(QDialog):
    """Dialog showing activity statistics."""

    def __init__(self, daily_stats: Dict[str, Any], weekly_stats: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Burnout Monitor - Stats")
        self.setMinimumWidth(350)
        self._setup_ui(daily_stats, weekly_stats)

    def _setup_ui(self, daily: Dict[str, Any], weekly: Dict[str, Any]) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Title
        title = QLabel("Activity Statistics")
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        # Today's stats
        today_frame = self._create_section("Today", [
            ("Hours worked", f"{daily.get('total_hours', 0)}h"),
            ("Pomodoros", str(daily.get('pomodoros_completed', daily.get('pomodoros', 0)))),
            ("Focus time", f"{daily.get('pomodoro_minutes', 0)}m"),
            ("Breaks taken", str(daily.get('breaks_taken', 0))),
            ("Files touched", str(daily.get('files_touched', 0))),
            ("Commits", str(daily.get('commits', 0))),
        ])
        layout.addWidget(today_frame)

        # Weekly stats
        week_frame = self._create_section("This Week", [
            ("Total hours", f"{weekly.get('total_hours', 0)}h"),
            ("Days worked", str(weekly.get('days_worked', 0))),
            ("Avg hours/day", f"{weekly.get('average_hours_per_day', 0)}h"),
        ])
        layout.addWidget(week_frame)

        # Weekly breakdown
        if weekly.get("daily_breakdown"):
            breakdown_frame = self._create_weekly_chart(weekly["daily_breakdown"])
            layout.addWidget(breakdown_frame)

        # Close button
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn)

        self.setLayout(layout)

        # Style
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #ffffff;
            }
            QFrame {
                background-color: #3d3d3d;
                border-radius: 8px;
                padding: 10px;
            }
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)

    def _create_section(self, title: str, items: List[tuple]) -> QFrame:
        """Create a stats section."""
        frame = QFrame()
        layout = QVBoxLayout()

        # Section title
        title_label = QLabel(title)
        title_font = QFont()
        title_font.setBold(True)
        title_font.setPointSize(12)
        title_label.setFont(title_font)
        title_label.setStyleSheet("color: #6bff8a;")
        layout.addWidget(title_label)

        # Stats grid
        grid = QGridLayout()
        grid.setSpacing(8)

        for i, (label, value) in enumerate(items):
            label_widget = QLabel(label)
            label_widget.setStyleSheet("color: #888888;")
            grid.addWidget(label_widget, i, 0)

            value_widget = QLabel(value)
            value_widget.setStyleSheet("color: #ffffff; font-weight: bold;")
            value_widget.setAlignment(Qt.AlignmentFlag.AlignRight)
            grid.addWidget(value_widget, i, 1)

        layout.addLayout(grid)
        frame.setLayout(layout)
        return frame

    def _create_weekly_chart(self, breakdown: List[Dict[str, Any]]) -> QFrame:
        """Create a simple weekly bar chart."""
        frame = QFrame()
        layout = QVBoxLayout()

        title = QLabel("Daily Breakdown")
        title_font = QFont()
        title_font.setBold(True)
        title.setFont(title_font)
        title.setStyleSheet("color: #6bb3ff;")
        layout.addWidget(title)

        # Bar chart
        chart_layout = QHBoxLayout()
        chart_layout.setSpacing(4)

        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        max_minutes = max((d.get("total_minutes", 0) for d in breakdown), default=480)
        max_minutes = max(max_minutes, 60)  # Minimum scale

        for i, day_data in enumerate(breakdown[-7:]):  # Last 7 days
            day_layout = QVBoxLayout()
            day_layout.setSpacing(2)

            # Bar
            minutes = day_data.get("total_minutes", 0)
            height = int((minutes / max_minutes) * 60)
            height = max(height, 2)  # Minimum visible height

            bar = QLabel()
            bar.setFixedSize(30, height)
            color = "#4CAF50" if minutes <= 480 else "#ff6b6b"  # Red if > 8h
            bar.setStyleSheet(f"background-color: {color}; border-radius: 3px;")
            day_layout.addWidget(bar, alignment=Qt.AlignmentFlag.AlignBottom)

            # Hours label
            hours = round(minutes / 60, 1)
            hours_label = QLabel(f"{hours}h")
            hours_label.setStyleSheet("color: #888888; font-size: 10px;")
            hours_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            day_layout.addWidget(hours_label)

            chart_layout.addLayout(day_layout)

        layout.addLayout(chart_layout)
        frame.setLayout(layout)
        return frame
