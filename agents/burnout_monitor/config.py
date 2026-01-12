"""Configuration for Burnout Monitor."""

CONFIG = {
    # Work hours (24h format)
    "work_start_hour": 9,
    "work_end_hour": 18,

    # Pomodoro settings
    "pomodoro_enabled": True,
    "pomodoro_work_minutes": 35,  # Work session duration
    "pomodoro_short_break": 5,    # Short break duration
    "pomodoro_long_break": 15,    # Long break (after 4 pomodoros)
    "pomodoros_until_long_break": 4,
    "break_extend_minutes": 5,    # Minutes to add when extending break

    # Break reminders (used when pomodoro is disabled)
    "break_reminder_interval": 90,  # minutes
    "break_duration": 10,  # minutes suggested break

    # Notifications
    "play_sound": True,  # Play sound on break
    "show_popup": True,  # Show big popup on break

    # Thresholds
    "max_daily_hours": 8,  # warn if exceeded
    "max_weekly_hours": 40,  # warn if exceeded
    "context_switch_threshold": 10,  # files in 15 min = high switching

    # Monitoring
    "watch_directories": [],  # empty = watch all, or specify paths
    "exclude_directories": [".git", "node_modules", "venv", "__pycache__", ".venv"],
    "track_git": True,
    "track_file_saves": True,

    # UI
    "widget_opacity": 0.95,
    "widget_position": "top-right",  # top-right, top-left, bottom-right, bottom-left

    # Notifications
    "enable_break_reminders": True,
    "enable_overtime_warnings": True,
    "gentle_mode": True,  # softer, friendlier messages

    # Data
    "data_retention_days": 90,  # how long to keep history
}

# Friendly messages for gentle mode
MESSAGES = {
    "break_reminder": [
        "You've been focused for {hours}h {mins}m. Good time for a stretch?",
        "Nice flow! {hours}h {mins}m in. Your brain might like a quick break.",
        "Deep work: {hours}h {mins}m. Coffee? Walk? Just a thought.",
    ],
    "overtime_warning": [
        "Big day - {hours} hours. Wrapping up soon?",
        "You've put in {hours} hours today. Tomorrow will thank you for rest.",
        "{hours} hours logged. You've earned some downtime.",
    ],
    "weekend_warning": [
        "It's the weekend! Just noticed you're working.",
        "Weekend coding detected. Passion project or should you unplug?",
    ],
    "late_night": [
        "It's {time}. Your code will still be here tomorrow.",
        "Late night session. Remember: sleep is a feature, not a bug.",
    ],
    "stuck_detection": [
        "45 min on the same area. Want to step back and rethink?",
        "Noticed you've been here a while. Sometimes a break brings clarity.",
    ],
}
