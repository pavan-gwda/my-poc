"""Activity monitoring for file saves and git operations."""

import os
import threading
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Callable, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent


class FileActivityHandler(FileSystemEventHandler):
    """Handles file system events."""

    def __init__(
        self,
        on_file_save: Callable[[str], None],
        exclude_dirs: Set[str],
        exclude_extensions: Set[str] = None
    ):
        self.on_file_save = on_file_save
        self.exclude_dirs = exclude_dirs
        self.exclude_extensions = exclude_extensions or {
            ".pyc", ".pyo", ".log", ".tmp", ".swp", ".swo",
            ".DS_Store", ".git", ".db", ".sqlite"
        }
        self._last_event_time = {}
        self._debounce_ms = 1000  # Ignore duplicate events within 1 second

    def _should_ignore(self, path: str) -> bool:
        """Check if path should be ignored."""
        path_obj = Path(path)

        # Check extension
        if path_obj.suffix in self.exclude_extensions:
            return True

        # Check if in excluded directory
        for part in path_obj.parts:
            if part in self.exclude_dirs:
                return True

        return False

    def _is_debounced(self, path: str) -> bool:
        """Check if event should be debounced."""
        now = datetime.now().timestamp() * 1000
        last_time = self._last_event_time.get(path, 0)

        if now - last_time < self._debounce_ms:
            return True

        self._last_event_time[path] = now
        return False

    def on_modified(self, event):
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            if not self._should_ignore(event.src_path) and not self._is_debounced(event.src_path):
                self.on_file_save(event.src_path)

    def on_created(self, event):
        if isinstance(event, FileCreatedEvent) and not event.is_directory:
            if not self._should_ignore(event.src_path) and not self._is_debounced(event.src_path):
                self.on_file_save(event.src_path)


class GitMonitor:
    """Monitors git activity."""

    def __init__(self, on_commit: Callable[[str, str], None]):
        self.on_commit = on_commit
        self._last_commit_hash = {}
        self._running = False
        self._thread: Optional[threading.Thread] = None

    def start(self, watch_dirs: list[str]) -> None:
        """Start monitoring git repositories."""
        self._running = True
        self._watch_dirs = watch_dirs
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

    def _monitor_loop(self) -> None:
        """Main monitoring loop."""
        import time
        while self._running:
            for directory in self._watch_dirs:
                self._check_git_activity(directory)
            time.sleep(30)  # Check every 30 seconds

    def _check_git_activity(self, directory: str) -> None:
        """Check for new git commits."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=directory,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0:
                current_hash = result.stdout.strip()
                last_hash = self._last_commit_hash.get(directory)

                if last_hash and current_hash != last_hash:
                    # New commit detected
                    msg_result = subprocess.run(
                        ["git", "log", "-1", "--pretty=%s"],
                        cwd=directory,
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    message = msg_result.stdout.strip() if msg_result.returncode == 0 else ""
                    self.on_commit(directory, message)

                self._last_commit_hash[directory] = current_hash
        except Exception:
            pass  # Not a git repo or git not available


class ActivityMonitor:
    """Main activity monitor combining file and git tracking."""

    def __init__(
        self,
        on_activity: Callable[[str, str, Optional[str]], None],
        watch_directories: list[str] = None,
        exclude_directories: Set[str] = None
    ):
        """
        Initialize activity monitor.

        Args:
            on_activity: Callback(event_type, file_path, project)
            watch_directories: Directories to watch (None = home directory)
            exclude_directories: Directories to exclude
        """
        self.on_activity = on_activity
        self.watch_directories = watch_directories or [str(Path.home())]
        self.exclude_directories = exclude_directories or {
            ".git", "node_modules", "venv", "__pycache__",
            ".venv", ".idea", ".vscode", "dist", "build"
        }

        self._observer: Optional[Observer] = None
        self._git_monitor: Optional[GitMonitor] = None
        self._running = False

    def start(self) -> None:
        """Start monitoring activity."""
        if self._running:
            return

        self._running = True

        # File monitoring
        self._observer = Observer()
        handler = FileActivityHandler(
            on_file_save=self._on_file_save,
            exclude_dirs=self.exclude_directories
        )

        for directory in self.watch_directories:
            if os.path.exists(directory):
                self._observer.schedule(handler, directory, recursive=True)

        self._observer.start()

        # Git monitoring
        self._git_monitor = GitMonitor(on_commit=self._on_git_commit)
        self._git_monitor.start(self.watch_directories)

        print(f"Activity monitor started. Watching: {self.watch_directories}")

    def stop(self) -> None:
        """Stop monitoring."""
        self._running = False

        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=2)
            self._observer = None

        if self._git_monitor:
            self._git_monitor.stop()
            self._git_monitor = None

    def _on_file_save(self, file_path: str) -> None:
        """Handle file save event."""
        project = self._detect_project(file_path)
        self.on_activity("file_save", file_path, project)

    def _on_git_commit(self, directory: str, message: str) -> None:
        """Handle git commit event."""
        project = os.path.basename(directory)
        self.on_activity("commit", directory, project)

    def _detect_project(self, file_path: str) -> Optional[str]:
        """Try to detect project name from file path."""
        path = Path(file_path)

        # Look for common project indicators
        for parent in path.parents:
            # Check for package.json, setup.py, Cargo.toml, etc.
            indicators = [
                "package.json", "setup.py", "pyproject.toml",
                "Cargo.toml", "go.mod", "pom.xml", ".git"
            ]
            for indicator in indicators:
                if (parent / indicator).exists():
                    return parent.name

        return None
