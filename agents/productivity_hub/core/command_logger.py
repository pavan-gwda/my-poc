"""Command logging for audit trail."""

import sqlite3
from pathlib import Path
from datetime import datetime
from typing import Optional, List, Dict, Any


class CommandLogger:
    """Logs all voice commands and STT transcriptions for auditing."""

    def __init__(self, db_path: Optional[Path] = None):
        if db_path is None:
            db_path = Path(__file__).parent.parent / "data" / "command_history.db"

        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        """Initialize the database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS voice_commands (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transcribed_text TEXT NOT NULL,
                    command_type TEXT,
                    command_params TEXT,
                    success INTEGER,
                    result_message TEXT,
                    execution_time_ms INTEGER
                )
            """)

            conn.execute("""
                CREATE TABLE IF NOT EXISTS stt_transcriptions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    transcribed_text TEXT NOT NULL,
                    word_count INTEGER,
                    audio_duration_ms INTEGER
                )
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_vc_timestamp ON voice_commands(timestamp)
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_stt_timestamp ON stt_transcriptions(timestamp)
            """)

            conn.commit()

    def log_voice_command(
        self,
        transcribed_text: str,
        command_type: str,
        command_params: Dict[str, Any],
        success: bool,
        result_message: str,
        execution_time_ms: int = 0
    ) -> None:
        """Log a voice command execution."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO voice_commands
                (transcribed_text, command_type, command_params, success, result_message, execution_time_ms)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                transcribed_text,
                command_type,
                json.dumps(command_params),
                1 if success else 0,
                result_message,
                execution_time_ms
            ))
            conn.commit()

    def log_stt_transcription(
        self,
        transcribed_text: str,
        word_count: int,
        audio_duration_ms: int = 0
    ) -> None:
        """Log an STT transcription."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO stt_transcriptions
                (transcribed_text, word_count, audio_duration_ms)
                VALUES (?, ?, ?)
            """, (transcribed_text, word_count, audio_duration_ms))
            conn.commit()

    def get_voice_command_history(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get voice command history."""
        import json

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM voice_commands
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            results = []
            for row in cursor.fetchall():
                results.append({
                    "id": row["id"],
                    "timestamp": row["timestamp"],
                    "transcribed_text": row["transcribed_text"],
                    "command_type": row["command_type"],
                    "command_params": json.loads(row["command_params"]) if row["command_params"] else {},
                    "success": bool(row["success"]),
                    "result_message": row["result_message"],
                    "execution_time_ms": row["execution_time_ms"]
                })
            return results

    def get_stt_history(
        self,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """Get STT transcription history."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM stt_transcriptions
                ORDER BY timestamp DESC
                LIMIT ? OFFSET ?
            """, (limit, offset))

            return [dict(row) for row in cursor.fetchall()]

    def get_today_stats(self) -> Dict[str, Any]:
        """Get today's command statistics."""
        today = datetime.now().strftime("%Y-%m-%d")

        with sqlite3.connect(self.db_path) as conn:
            # Voice commands stats
            vc_cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                    SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
                FROM voice_commands
                WHERE DATE(timestamp) = ?
            """, (today,))
            vc_row = vc_cursor.fetchone()

            # STT stats
            stt_cursor = conn.execute("""
                SELECT
                    COUNT(*) as total,
                    SUM(word_count) as total_words
                FROM stt_transcriptions
                WHERE DATE(timestamp) = ?
            """, (today,))
            stt_row = stt_cursor.fetchone()

            # Most used commands
            cmd_cursor = conn.execute("""
                SELECT command_type, COUNT(*) as count
                FROM voice_commands
                WHERE DATE(timestamp) = ?
                GROUP BY command_type
                ORDER BY count DESC
                LIMIT 5
            """, (today,))

            return {
                "voice_commands": {
                    "total": vc_row[0] or 0,
                    "successful": vc_row[1] or 0,
                    "failed": vc_row[2] or 0
                },
                "stt": {
                    "total": stt_row[0] or 0,
                    "total_words": stt_row[1] or 0
                },
                "top_commands": [
                    {"command": row[0], "count": row[1]}
                    for row in cmd_cursor.fetchall()
                ]
            }

    def export_to_csv(self, output_path: Path, table: str = "voice_commands") -> None:
        """Export history to CSV for external auditing."""
        import csv

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(f"SELECT * FROM {table} ORDER BY timestamp DESC")
            rows = cursor.fetchall()

            if rows:
                with open(output_path, 'w', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=rows[0].keys())
                    writer.writeheader()
                    for row in rows:
                        writer.writerow(dict(row))
