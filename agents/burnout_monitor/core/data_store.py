"""SQLite data store for activity tracking."""

import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from pathlib import Path


class DataStore:
    """Manages persistent storage of activity data."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            data_dir = Path(__file__).parent.parent / "data"
            data_dir.mkdir(exist_ok=True)
            db_path = str(data_dir / "burnout_monitor.db")

        self.db_path = db_path
        self._init_db()

    def _init_db(self) -> None:
        """Initialize database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS sessions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_minutes INTEGER,
                    date TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS activity_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP NOT NULL,
                    event_type TEXT NOT NULL,
                    file_path TEXT,
                    project TEXT,
                    metadata TEXT,
                    date TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS daily_stats (
                    date TEXT PRIMARY KEY,
                    total_minutes INTEGER DEFAULT 0,
                    files_touched INTEGER DEFAULT 0,
                    commits INTEGER DEFAULT 0,
                    context_switches INTEGER DEFAULT 0,
                    breaks_taken INTEGER DEFAULT 0,
                    first_activity TEXT,
                    last_activity TEXT
                );

                CREATE TABLE IF NOT EXISTS breaks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    duration_minutes INTEGER,
                    date TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pomodoros (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    completed_at TIMESTAMP NOT NULL,
                    work_minutes INTEGER NOT NULL,
                    date TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_events_date ON activity_events(date);
                CREATE INDEX IF NOT EXISTS idx_pomodoros_date ON pomodoros(date);
                CREATE INDEX IF NOT EXISTS idx_events_timestamp ON activity_events(timestamp);
                CREATE INDEX IF NOT EXISTS idx_sessions_date ON sessions(date);
            """)

    def start_session(self) -> int:
        """Start a new coding session."""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "INSERT INTO sessions (start_time, date) VALUES (?, ?)",
                (now.isoformat(), now.strftime("%Y-%m-%d"))
            )
            return cursor.lastrowid

    def end_session(self, session_id: int) -> None:
        """End a coding session."""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                UPDATE sessions
                SET end_time = ?,
                    duration_minutes = ROUND((JULIANDAY(?) - JULIANDAY(start_time)) * 1440)
                WHERE id = ?
            """, (now.isoformat(), now.isoformat(), session_id))

    def log_activity(
        self,
        event_type: str,
        file_path: Optional[str] = None,
        project: Optional[str] = None,
        metadata: Optional[str] = None
    ) -> None:
        """Log an activity event."""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO activity_events
                   (timestamp, event_type, file_path, project, metadata, date)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (now.isoformat(), event_type, file_path, project, metadata, now.strftime("%Y-%m-%d"))
            )

    def log_break(self, duration_minutes: int) -> None:
        """Log a break taken."""
        now = datetime.now()
        start_time = now - timedelta(minutes=duration_minutes)
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO breaks (start_time, end_time, duration_minutes, date)
                   VALUES (?, ?, ?, ?)""",
                (start_time.isoformat(), now.isoformat(), duration_minutes, now.strftime("%Y-%m-%d"))
            )

    def log_pomodoro(self, work_minutes: int) -> None:
        """Log a completed pomodoro session."""
        now = datetime.now()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """INSERT INTO pomodoros (completed_at, work_minutes, date)
                   VALUES (?, ?, ?)""",
                (now.isoformat(), work_minutes, now.strftime("%Y-%m-%d"))
            )

    def get_today_pomodoros(self) -> Dict[str, Any]:
        """Get pomodoro stats for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(work_minutes), 0) as total_minutes
                FROM pomodoros WHERE date = ?
            """, (today,)).fetchone()

            return {
                "count": result[0] or 0,
                "total_minutes": result[1] or 0,
            }

    def get_today_stats(self) -> Dict[str, Any]:
        """Get statistics for today."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row

            # Get session time
            session_result = conn.execute("""
                SELECT COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM sessions WHERE date = ?
            """, (today,)).fetchone()

            # Get active session time
            active_session = conn.execute("""
                SELECT start_time FROM sessions
                WHERE date = ? AND end_time IS NULL
                ORDER BY start_time DESC LIMIT 1
            """, (today,)).fetchone()

            active_minutes = 0
            if active_session:
                start = datetime.fromisoformat(active_session["start_time"])
                active_minutes = int((datetime.now() - start).total_seconds() / 60)

            # Get event counts
            events = conn.execute("""
                SELECT
                    COUNT(DISTINCT file_path) as files_touched,
                    SUM(CASE WHEN event_type = 'commit' THEN 1 ELSE 0 END) as commits,
                    MIN(timestamp) as first_activity,
                    MAX(timestamp) as last_activity
                FROM activity_events WHERE date = ?
            """, (today,)).fetchone()

            # Get breaks
            breaks = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(duration_minutes), 0) as total
                FROM breaks WHERE date = ?
            """, (today,)).fetchone()

            # Get pomodoros
            pomodoros = conn.execute("""
                SELECT COUNT(*) as count, COALESCE(SUM(work_minutes), 0) as total
                FROM pomodoros WHERE date = ?
            """, (today,)).fetchone()

            # Calculate context switches (file changes within 15 min windows)
            switches = conn.execute("""
                SELECT COUNT(DISTINCT file_path) as switches
                FROM activity_events
                WHERE date = ? AND event_type = 'file_save'
                AND timestamp > datetime('now', '-15 minutes')
            """, (today,)).fetchone()

            total_minutes = (session_result["total_minutes"] or 0) + active_minutes

            return {
                "date": today,
                "total_minutes": total_minutes,
                "total_hours": round(total_minutes / 60, 1),
                "files_touched": events["files_touched"] or 0,
                "commits": events["commits"] or 0,
                "breaks_taken": breaks["count"] or 0,
                "break_minutes": breaks["total"] or 0,
                "pomodoros_completed": pomodoros[0] or 0,
                "pomodoro_minutes": pomodoros[1] or 0,
                "first_activity": events["first_activity"],
                "last_activity": events["last_activity"],
                "recent_context_switches": switches["switches"] or 0,
                "has_active_session": active_session is not None,
                "active_session_minutes": active_minutes,
            }

    def get_weekly_stats(self) -> List[Dict[str, Any]]:
        """Get statistics for the past 7 days."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            results = conn.execute("""
                SELECT
                    date,
                    COALESCE(SUM(duration_minutes), 0) as total_minutes
                FROM sessions
                WHERE date >= date('now', '-7 days')
                GROUP BY date
                ORDER BY date
            """).fetchall()

            return [dict(row) for row in results]

    def get_current_session_duration(self) -> int:
        """Get duration of current active session in minutes."""
        today = datetime.now().strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT start_time FROM sessions
                WHERE date = ? AND end_time IS NULL
                ORDER BY start_time DESC LIMIT 1
            """, (today,)).fetchone()

            if result:
                start = datetime.fromisoformat(result[0])
                return int((datetime.now() - start).total_seconds() / 60)
            return 0

    def get_time_since_last_break(self) -> int:
        """Get minutes since last break."""
        with sqlite3.connect(self.db_path) as conn:
            result = conn.execute("""
                SELECT end_time FROM breaks
                ORDER BY end_time DESC LIMIT 1
            """).fetchone()

            if result:
                last_break = datetime.fromisoformat(result[0])
                return int((datetime.now() - last_break).total_seconds() / 60)

            # If no breaks, use session start
            result = conn.execute("""
                SELECT start_time FROM sessions
                WHERE end_time IS NULL
                ORDER BY start_time DESC LIMIT 1
            """).fetchone()

            if result:
                start = datetime.fromisoformat(result[0])
                return int((datetime.now() - start).total_seconds() / 60)

            return 0

    def cleanup_old_data(self, retention_days: int) -> None:
        """Remove data older than retention period."""
        cutoff = (datetime.now() - timedelta(days=retention_days)).strftime("%Y-%m-%d")
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM sessions WHERE date < ?", (cutoff,))
            conn.execute("DELETE FROM activity_events WHERE date < ?", (cutoff,))
            conn.execute("DELETE FROM breaks WHERE date < ?", (cutoff,))
            conn.execute("DELETE FROM pomodoros WHERE date < ?", (cutoff,))
            conn.execute("DELETE FROM daily_stats WHERE date < ?", (cutoff,))
            conn.commit()
        # VACUUM must run outside a transaction
        with sqlite3.connect(self.db_path, isolation_level=None) as conn:
            conn.execute("VACUUM")
