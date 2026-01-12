"""Analysis engine for burnout detection."""

import random
from datetime import datetime
from typing import Dict, Any, Optional, List
from .data_store import DataStore


class AnalysisEngine:
    """Analyzes activity patterns and detects burnout signals."""

    def __init__(self, data_store: DataStore, config: Dict[str, Any]):
        self.data_store = data_store
        self.config = config
        self._messages = config.get("messages", {})

    def get_status(self) -> Dict[str, Any]:
        """Get current status summary."""
        stats = self.data_store.get_today_stats()
        session_minutes = self.data_store.get_current_session_duration()
        since_break = self.data_store.get_time_since_last_break()

        # Determine status level
        status = "good"
        if since_break > self.config.get("break_reminder_interval", 90):
            status = "needs_break"
        if stats["total_hours"] > self.config.get("max_daily_hours", 8):
            status = "overtime"

        return {
            "status": status,
            "session_minutes": session_minutes,
            "session_hours": round(session_minutes / 60, 1),
            "today_minutes": stats["total_minutes"],
            "today_hours": stats["total_hours"],
            "since_break_minutes": since_break,
            "files_touched": stats["files_touched"],
            "commits": stats["commits"],
            "breaks_taken": stats["breaks_taken"],
            "context_switches": stats["recent_context_switches"],
        }

    def check_alerts(self) -> List[Dict[str, Any]]:
        """Check for conditions that need alerts."""
        alerts = []
        status = self.get_status()
        now = datetime.now()

        # Break reminder
        if status["since_break_minutes"] >= self.config.get("break_reminder_interval", 90):
            hours = status["since_break_minutes"] // 60
            mins = status["since_break_minutes"] % 60
            alerts.append({
                "type": "break_reminder",
                "severity": "info",
                "message": self._get_message("break_reminder", hours=hours, mins=mins),
            })

        # Overtime warning
        max_hours = self.config.get("max_daily_hours", 8)
        if status["today_hours"] > max_hours:
            alerts.append({
                "type": "overtime",
                "severity": "warning",
                "message": self._get_message("overtime_warning", hours=status["today_hours"]),
            })

        # Late night warning
        if now.hour >= 22 or now.hour < 6:
            alerts.append({
                "type": "late_night",
                "severity": "info",
                "message": self._get_message("late_night", time=now.strftime("%I:%M %p")),
            })

        # Weekend warning
        if now.weekday() >= 5:  # Saturday = 5, Sunday = 6
            work_start = self.config.get("work_start_hour", 9)
            work_end = self.config.get("work_end_hour", 18)
            if not (work_start <= now.hour < work_end):
                alerts.append({
                    "type": "weekend",
                    "severity": "info",
                    "message": self._get_message("weekend_warning"),
                })

        # High context switching
        if status["context_switches"] > self.config.get("context_switch_threshold", 10):
            alerts.append({
                "type": "context_switching",
                "severity": "info",
                "message": "Lots of file switching detected. Feeling scattered?",
            })

        return alerts

    def get_daily_summary(self) -> Dict[str, Any]:
        """Generate daily summary."""
        stats = self.data_store.get_today_stats()

        # Productivity assessment
        hours = stats["total_hours"]
        if hours < 4:
            productivity = "light"
        elif hours < 6:
            productivity = "moderate"
        elif hours < 8:
            productivity = "productive"
        else:
            productivity = "heavy"

        return {
            "date": stats["date"],
            "total_hours": hours,
            "productivity": productivity,
            "files_touched": stats["files_touched"],
            "commits": stats["commits"],
            "breaks_taken": stats["breaks_taken"],
            "first_activity": stats["first_activity"],
            "last_activity": stats["last_activity"],
            "summary": self._generate_summary_text(stats),
        }

    def get_weekly_summary(self) -> Dict[str, Any]:
        """Generate weekly summary."""
        weekly_stats = self.data_store.get_weekly_stats()

        total_minutes = sum(day.get("total_minutes", 0) for day in weekly_stats)
        total_hours = round(total_minutes / 60, 1)
        days_worked = len([d for d in weekly_stats if d.get("total_minutes", 0) > 0])
        avg_hours = round(total_hours / max(days_worked, 1), 1)

        return {
            "total_hours": total_hours,
            "days_worked": days_worked,
            "average_hours_per_day": avg_hours,
            "daily_breakdown": weekly_stats,
            "over_threshold": total_hours > self.config.get("max_weekly_hours", 40),
        }

    def _get_message(self, message_type: str, **kwargs) -> str:
        """Get a random message of the given type."""
        from config import MESSAGES
        messages = MESSAGES.get(message_type, [f"Alert: {message_type}"])
        template = random.choice(messages)
        return template.format(**kwargs)

    def _generate_summary_text(self, stats: Dict[str, Any]) -> str:
        """Generate human-readable summary."""
        hours = stats["total_hours"]
        files = stats["files_touched"]
        commits = stats["commits"]
        breaks = stats["breaks_taken"]

        parts = []
        parts.append(f"{hours} hours of coding")

        if files > 0:
            parts.append(f"{files} files touched")
        if commits > 0:
            parts.append(f"{commits} commits")
        if breaks > 0:
            parts.append(f"{breaks} breaks taken")

        return ", ".join(parts) + "."
