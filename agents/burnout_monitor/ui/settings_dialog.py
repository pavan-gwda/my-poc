"""Settings dialog for configuring Burnout Monitor."""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QCheckBox,
    QComboBox,
    QGroupBox,
    QFormLayout,
    QTabWidget,
    QWidget,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from typing import Dict, Any


class SettingsDialog(QDialog):
    """Dialog for configuring app settings."""

    settings_changed = pyqtSignal(dict)  # Emits updated settings

    def __init__(self, current_settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.settings = current_settings.copy()
        self.setWindowTitle("Settings")
        self.setMinimumWidth(400)
        self._setup_ui()

    def _setup_ui(self) -> None:
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Tab widget for organized settings
        tabs = QTabWidget()

        # Pomodoro tab
        pomodoro_tab = self._create_pomodoro_tab()
        tabs.addTab(pomodoro_tab, "Pomodoro")

        # Notifications tab
        notifications_tab = self._create_notifications_tab()
        tabs.addTab(notifications_tab, "Notifications")

        # Appearance tab
        appearance_tab = self._create_appearance_tab()
        tabs.addTab(appearance_tab, "Appearance")

        # Voice tab
        voice_tab = self._create_voice_tab()
        tabs.addTab(voice_tab, "Voice")

        layout.addWidget(tabs)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self._save_settings)
        save_btn.setDefault(True)
        button_layout.addWidget(save_btn)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # Styling
        self.setStyleSheet("""
            QDialog {
                background-color: #2d2d2d;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #6bff8a;
                font-weight: bold;
                border: 1px solid #3d3d3d;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QSpinBox, QComboBox {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 5px;
                min-width: 80px;
            }
            QCheckBox {
                color: #ffffff;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                background-color: #3d3d3d;
                border: 1px solid #4d4d4d;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border: 1px solid #4CAF50;
                border-radius: 3px;
            }
            QPushButton {
                background-color: #4d4d4d;
                color: white;
                border: none;
                padding: 8px 20px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #5d5d5d;
            }
            QPushButton:default {
                background-color: #4CAF50;
            }
            QPushButton:default:hover {
                background-color: #45a049;
            }
            QTabWidget::pane {
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                background-color: #2d2d2d;
            }
            QTabBar::tab {
                background-color: #3d3d3d;
                color: #888888;
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4d4d4d;
                color: #ffffff;
            }
        """)

    def _create_pomodoro_tab(self) -> QWidget:
        """Create pomodoro settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Enable pomodoro
        self.pomodoro_enabled = QCheckBox("Enable Pomodoro Timer")
        self.pomodoro_enabled.setChecked(self.settings.get("pomodoro_enabled", True))
        layout.addWidget(self.pomodoro_enabled)

        # Timer settings group
        timer_group = QGroupBox("Timer Durations")
        timer_layout = QFormLayout()

        # Work duration
        self.work_minutes = QSpinBox()
        self.work_minutes.setRange(1, 120)
        self.work_minutes.setValue(self.settings.get("pomodoro_work_minutes", 25))
        self.work_minutes.setSuffix(" min")
        timer_layout.addRow("Work session:", self.work_minutes)

        # Short break
        self.short_break = QSpinBox()
        self.short_break.setRange(1, 30)
        self.short_break.setValue(self.settings.get("pomodoro_short_break", 5))
        self.short_break.setSuffix(" min")
        timer_layout.addRow("Short break:", self.short_break)

        # Long break
        self.long_break = QSpinBox()
        self.long_break.setRange(5, 60)
        self.long_break.setValue(self.settings.get("pomodoro_long_break", 15))
        self.long_break.setSuffix(" min")
        timer_layout.addRow("Long break:", self.long_break)

        # Pomodoros until long break
        self.pomodoros_count = QSpinBox()
        self.pomodoros_count.setRange(2, 10)
        self.pomodoros_count.setValue(self.settings.get("pomodoros_until_long_break", 4))
        timer_layout.addRow("Pomodoros until long break:", self.pomodoros_count)

        # Extend break duration
        self.extend_minutes = QSpinBox()
        self.extend_minutes.setRange(1, 30)
        self.extend_minutes.setValue(self.settings.get("break_extend_minutes", 5))
        self.extend_minutes.setSuffix(" min")
        timer_layout.addRow("Extend break by:", self.extend_minutes)

        timer_group.setLayout(timer_layout)
        layout.addWidget(timer_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_notifications_tab(self) -> QWidget:
        """Create notifications settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Sound settings
        sound_group = QGroupBox("Sound")
        sound_layout = QVBoxLayout()

        self.play_sound = QCheckBox("Play sound on break")
        self.play_sound.setChecked(self.settings.get("play_sound", True))
        sound_layout.addWidget(self.play_sound)

        sound_group.setLayout(sound_layout)
        layout.addWidget(sound_group)

        # Popup settings
        popup_group = QGroupBox("Popup")
        popup_layout = QVBoxLayout()

        self.show_popup = QCheckBox("Show popup on break")
        self.show_popup.setChecked(self.settings.get("show_popup", True))
        popup_layout.addWidget(self.show_popup)

        popup_group.setLayout(popup_layout)
        layout.addWidget(popup_group)

        # Reminders group
        reminder_group = QGroupBox("Reminders (when Pomodoro disabled)")
        reminder_layout = QFormLayout()

        self.break_interval = QSpinBox()
        self.break_interval.setRange(15, 180)
        self.break_interval.setValue(self.settings.get("break_reminder_interval", 90))
        self.break_interval.setSuffix(" min")
        reminder_layout.addRow("Remind every:", self.break_interval)

        self.overtime_warning = QCheckBox("Warn on overtime")
        self.overtime_warning.setChecked(self.settings.get("enable_overtime_warnings", True))
        reminder_layout.addRow(self.overtime_warning)

        reminder_group.setLayout(reminder_layout)
        layout.addWidget(reminder_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_appearance_tab(self) -> QWidget:
        """Create appearance settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Position settings
        position_group = QGroupBox("Widget Position")
        position_layout = QFormLayout()

        self.widget_position = QComboBox()
        self.widget_position.addItems(["top-right", "top-left", "bottom-right", "bottom-left"])
        current_pos = self.settings.get("widget_position", "top-right")
        self.widget_position.setCurrentText(current_pos)
        position_layout.addRow("Position:", self.widget_position)

        position_group.setLayout(position_layout)
        layout.addWidget(position_group)

        # Work hours group
        hours_group = QGroupBox("Work Hours")
        hours_layout = QFormLayout()

        self.work_start = QSpinBox()
        self.work_start.setRange(0, 23)
        self.work_start.setValue(self.settings.get("work_start_hour", 9))
        self.work_start.setSuffix(":00")
        hours_layout.addRow("Start:", self.work_start)

        self.work_end = QSpinBox()
        self.work_end.setRange(0, 23)
        self.work_end.setValue(self.settings.get("work_end_hour", 18))
        self.work_end.setSuffix(":00")
        hours_layout.addRow("End:", self.work_end)

        self.max_daily = QSpinBox()
        self.max_daily.setRange(1, 16)
        self.max_daily.setValue(self.settings.get("max_daily_hours", 8))
        self.max_daily.setSuffix(" hours")
        hours_layout.addRow("Max daily:", self.max_daily)

        hours_group.setLayout(hours_layout)
        layout.addWidget(hours_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _create_voice_tab(self) -> QWidget:
        """Create voice feedback settings tab."""
        widget = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Voice feedback enable/disable
        self.voice_enabled = QCheckBox("Enable Voice Feedback")
        self.voice_enabled.setChecked(self.settings.get("speak_feedback", True))
        layout.addWidget(self.voice_enabled)

        # Voice settings group
        voice_group = QGroupBox("Voice Settings")
        voice_layout = QFormLayout()

        # Voice selection
        self.voice_select = QComboBox()
        voices = ["Alex", "Samantha", "Victoria", "Daniel", "Karen", "Moira", "Tessa", "Veena", "Fiona"]
        self.voice_select.addItems(voices)
        current_voice = self.settings.get("voice_feedback_voice", "Alex")
        if current_voice in voices:
            self.voice_select.setCurrentText(current_voice)
        voice_layout.addRow("Voice:", self.voice_select)

        # Speech rate
        self.voice_rate = QSpinBox()
        self.voice_rate.setRange(100, 400)
        self.voice_rate.setValue(self.settings.get("voice_feedback_rate", 200))
        self.voice_rate.setSuffix(" wpm")
        voice_layout.addRow("Speed:", self.voice_rate)

        # Test button
        test_btn = QPushButton("Test Voice")
        test_btn.clicked.connect(self._test_voice)
        voice_layout.addRow("", test_btn)

        voice_group.setLayout(voice_layout)
        layout.addWidget(voice_group)

        # Wake Word settings group
        wake_group = QGroupBox("Wake Word (Hands-free Activation)")
        wake_layout = QVBoxLayout()

        # Enable wake word
        self.wake_word_enabled = QCheckBox("Enable Wake Word Detection")
        self.wake_word_enabled.setChecked(self.settings.get("wake_word_enabled", False))
        wake_layout.addWidget(self.wake_word_enabled)

        # Wake words list
        list_label = QLabel("Wake Words:")
        list_label.setStyleSheet("color: #888888; font-size: 11px;")
        wake_layout.addWidget(list_label)

        self.wake_words_list = QListWidget()
        self.wake_words_list.setMaximumHeight(80)
        self.wake_words_list.setStyleSheet("""
            QListWidget {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
            }
            QListWidget::item:selected {
                background-color: #4CAF50;
            }
        """)
        # Populate with current wake words
        current_wake_words = self.settings.get("wake_words", ["hey computer", "ok computer", "hello computer"])
        for word in current_wake_words:
            self.wake_words_list.addItem(word)
        wake_layout.addWidget(self.wake_words_list)

        # Add/Remove buttons
        btn_layout = QHBoxLayout()

        self.wake_word_input = QLineEdit()
        self.wake_word_input.setPlaceholderText("Enter new wake word...")
        self.wake_word_input.setStyleSheet("""
            QLineEdit {
                background-color: #3d3d3d;
                color: #ffffff;
                border: 1px solid #4d4d4d;
                border-radius: 4px;
                padding: 5px;
            }
        """)
        btn_layout.addWidget(self.wake_word_input)

        add_btn = QPushButton("Add")
        add_btn.clicked.connect(self._add_wake_word)
        btn_layout.addWidget(add_btn)

        remove_btn = QPushButton("Remove")
        remove_btn.clicked.connect(self._remove_wake_word)
        btn_layout.addWidget(remove_btn)

        wake_layout.addLayout(btn_layout)

        # Help text
        help_label = QLabel("Say a wake word to activate Voice Commander hands-free.")
        help_label.setStyleSheet("color: #666666; font-size: 10px;")
        wake_layout.addWidget(help_label)

        wake_group.setLayout(wake_layout)
        layout.addWidget(wake_group)

        layout.addStretch()
        widget.setLayout(layout)
        return widget

    def _add_wake_word(self) -> None:
        """Add a new wake word to the list."""
        word = self.wake_word_input.text().strip().lower()
        if word:
            # Check if already exists
            existing = [self.wake_words_list.item(i).text() for i in range(self.wake_words_list.count())]
            if word not in existing:
                self.wake_words_list.addItem(word)
                self.wake_word_input.clear()

    def _remove_wake_word(self) -> None:
        """Remove selected wake word from the list."""
        current_item = self.wake_words_list.currentItem()
        if current_item:
            row = self.wake_words_list.row(current_item)
            self.wake_words_list.takeItem(row)

    def _test_voice(self) -> None:
        """Test the selected voice."""
        import subprocess
        voice = self.voice_select.currentText()
        rate = self.voice_rate.value()
        try:
            subprocess.Popen(
                ["say", "-v", voice, "-r", str(rate), "Hello, I'm your voice assistant"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        except Exception:
            pass

    def _save_settings(self) -> None:
        """Save settings and close dialog."""
        # Update settings dict
        self.settings["pomodoro_enabled"] = self.pomodoro_enabled.isChecked()
        self.settings["pomodoro_work_minutes"] = self.work_minutes.value()
        self.settings["pomodoro_short_break"] = self.short_break.value()
        self.settings["pomodoro_long_break"] = self.long_break.value()
        self.settings["pomodoros_until_long_break"] = self.pomodoros_count.value()
        self.settings["break_extend_minutes"] = self.extend_minutes.value()

        self.settings["play_sound"] = self.play_sound.isChecked()
        self.settings["show_popup"] = self.show_popup.isChecked()
        self.settings["break_reminder_interval"] = self.break_interval.value()
        self.settings["enable_overtime_warnings"] = self.overtime_warning.isChecked()

        self.settings["widget_position"] = self.widget_position.currentText()
        self.settings["work_start_hour"] = self.work_start.value()
        self.settings["work_end_hour"] = self.work_end.value()
        self.settings["max_daily_hours"] = self.max_daily.value()

        # Voice settings
        self.settings["speak_feedback"] = self.voice_enabled.isChecked()
        self.settings["voice_feedback_voice"] = self.voice_select.currentText()
        self.settings["voice_feedback_rate"] = self.voice_rate.value()

        # Wake word settings
        self.settings["wake_word_enabled"] = self.wake_word_enabled.isChecked()
        wake_words = [self.wake_words_list.item(i).text() for i in range(self.wake_words_list.count())]
        self.settings["wake_words"] = wake_words if wake_words else ["hey computer"]

        # Emit signal with updated settings
        self.settings_changed.emit(self.settings)

        # Save to file
        self._save_to_file()

        self.accept()

    def _save_to_file(self) -> None:
        """Save settings to JSON file."""
        settings_path = Path(__file__).parent.parent / "data" / "settings.json"
        settings_path.parent.mkdir(exist_ok=True)

        # Filter out non-serializable objects (like sets for hotkeys)
        serializable_settings = {
            k: v for k, v in self.settings.items()
            if isinstance(v, (str, int, float, bool, list, dict, type(None)))
        }

        with open(settings_path, "w") as f:
            json.dump(serializable_settings, f, indent=2)

    @staticmethod
    def load_settings() -> Dict[str, Any]:
        """Load settings from JSON file, fall back to defaults."""
        from config import CONFIG

        settings_path = Path(__file__).parent.parent / "data" / "settings.json"

        if settings_path.exists():
            try:
                with open(settings_path) as f:
                    saved = json.load(f)
                    # Merge with defaults (saved takes precedence)
                    merged = CONFIG.copy()
                    merged.update(saved)
                    return merged
            except Exception:
                pass

        return CONFIG.copy()
