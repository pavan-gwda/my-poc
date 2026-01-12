"""Action executor for macOS system commands."""

import subprocess
import urllib.parse
from typing import Tuple
from .command_parser import ParsedCommand, CommandType


class ActionExecutor:
    """Executes parsed commands on macOS."""

    def execute(self, command: ParsedCommand) -> Tuple[bool, str]:
        """
        Execute a parsed command.
        Returns (success, message).
        """
        handlers = {
            CommandType.OPEN_APP: self._open_app,
            CommandType.CLOSE_APP: self._close_app,
            CommandType.SWITCH_APP: self._switch_app,
            CommandType.MINIMIZE_APP: self._minimize_app,

            CommandType.VOLUME_UP: self._volume_up,
            CommandType.VOLUME_DOWN: self._volume_down,
            CommandType.VOLUME_MUTE: self._volume_mute,
            CommandType.VOLUME_SET: self._volume_set,

            CommandType.BRIGHTNESS_UP: self._brightness_up,
            CommandType.BRIGHTNESS_DOWN: self._brightness_down,

            CommandType.SCREENSHOT: self._screenshot,
            CommandType.SCREENSHOT_AREA: self._screenshot_area,

            CommandType.SLEEP: self._sleep,
            CommandType.LOCK: self._lock,

            CommandType.SEARCH_WEB: self._search_web,
            CommandType.OPEN_URL: self._open_url,
            CommandType.OPEN_WEBSITE: self._open_website,

            CommandType.PLAY_PAUSE: self._play_pause,
            CommandType.NEXT_TRACK: self._next_track,
            CommandType.PREV_TRACK: self._prev_track,

            CommandType.UNKNOWN: self._unknown,
        }

        handler = handlers.get(command.command_type, self._unknown)
        return handler(command)

    def _run_osascript(self, script: str) -> Tuple[bool, str]:
        """Run an AppleScript command."""
        try:
            result = subprocess.run(
                ["osascript", "-e", script],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return True, result.stdout.strip()
            return False, result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    def _run_command(self, args: list) -> Tuple[bool, str]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                args,
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0, result.stdout.strip() or result.stderr.strip()
        except subprocess.TimeoutExpired:
            return False, "Command timed out"
        except Exception as e:
            return False, str(e)

    # App commands
    def _open_app(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Open an application."""
        app_name = cmd.params["app_name"]
        success, output = self._run_command(["open", "-a", app_name])
        if success:
            return True, f"Opened {app_name}"
        return False, f"Could not open {app_name}: {output}"

    def _close_app(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Close an application."""
        app_name = cmd.params["app_name"]
        script = f'tell application "{app_name}" to quit'
        success, output = self._run_osascript(script)
        if success:
            return True, f"Closed {app_name}"
        return False, f"Could not close {app_name}"

    def _switch_app(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Switch to (activate) an application."""
        app_name = cmd.params["app_name"]
        script = f'tell application "{app_name}" to activate'
        success, output = self._run_osascript(script)
        if success:
            return True, f"Switched to {app_name}"
        return False, f"Could not switch to {app_name}"

    def _minimize_app(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Minimize an application's windows."""
        app_name = cmd.params.get("app_name")

        if cmd.params.get("current") or not app_name:
            # Minimize current/frontmost window
            script = """
            tell application "System Events"
                set frontApp to name of first application process whose frontmost is true
                tell process frontApp
                    set value of attribute "AXMinimized" of window 1 to true
                end tell
            end tell
            return frontApp
            """
            success, output = self._run_osascript(script)
            if success:
                return True, f"Minimized {output}"
            return False, "Could not minimize current window"
        else:
            # Minimize specific app
            script = f"""
            tell application "System Events"
                if exists (process "{app_name}") then
                    tell process "{app_name}"
                        set windowCount to count of windows
                        if windowCount > 0 then
                            repeat with w in windows
                                set value of attribute "AXMinimized" of w to true
                            end repeat
                            return "Minimized " & windowCount & " window(s)"
                        else
                            return "No windows to minimize"
                        end if
                    end tell
                else
                    return "App not running"
                end if
            end tell
            """
            success, output = self._run_osascript(script)
            if success:
                if "not running" in output.lower():
                    return False, f"{app_name} is not running"
                return True, f"Minimized {app_name}"
            return False, f"Could not minimize {app_name}"

    # Volume commands
    def _volume_up(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Increase volume by 10%."""
        script = """
        set curVolume to output volume of (get volume settings)
        set volume output volume (curVolume + 10)
        """
        success, _ = self._run_osascript(script)
        return success, "Volume up" if success else "Could not change volume"

    def _volume_down(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Decrease volume by 10%."""
        script = """
        set curVolume to output volume of (get volume settings)
        set volume output volume (curVolume - 10)
        """
        success, _ = self._run_osascript(script)
        return success, "Volume down" if success else "Could not change volume"

    def _volume_mute(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Toggle mute."""
        script = """
        set curMuted to output muted of (get volume settings)
        set volume output muted (not curMuted)
        if curMuted then
            return "Unmuted"
        else
            return "Muted"
        end if
        """
        success, output = self._run_osascript(script)
        return success, output if success else "Could not toggle mute"

    def _volume_set(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Set volume to specific level."""
        level = cmd.params["level"]
        script = f"set volume output volume {level}"
        success, _ = self._run_osascript(script)
        return success, f"Volume set to {level}%" if success else "Could not set volume"

    # Brightness commands (requires brightness tool or uses keyboard simulation)
    def _brightness_up(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Increase brightness."""
        # Simulate brightness key press
        script = """
        tell application "System Events"
            key code 144
        end tell
        """
        success, _ = self._run_osascript(script)
        return success, "Brightness up" if success else "Could not change brightness"

    def _brightness_down(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Decrease brightness."""
        script = """
        tell application "System Events"
            key code 145
        end tell
        """
        success, _ = self._run_osascript(script)
        return success, "Brightness down" if success else "Could not change brightness"

    # Screenshot commands
    def _screenshot(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Take a full screenshot."""
        success, _ = self._run_command(["screencapture", "-x", f"~/Desktop/screenshot_{self._timestamp()}.png"])
        # Also use the standard keyboard shortcut method which saves to default location
        script = """
        tell application "System Events"
            keystroke "3" using {command down, shift down}
        end tell
        """
        success, _ = self._run_osascript(script)
        return success, "Screenshot taken" if success else "Could not take screenshot"

    def _screenshot_area(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Take a screenshot of selected area."""
        script = """
        tell application "System Events"
            keystroke "4" using {command down, shift down}
        end tell
        """
        success, _ = self._run_osascript(script)
        return success, "Select area for screenshot" if success else "Could not start screenshot"

    def _timestamp(self) -> str:
        """Get current timestamp for filenames."""
        from datetime import datetime
        return datetime.now().strftime("%Y%m%d_%H%M%S")

    # System commands
    def _sleep(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Put the Mac to sleep."""
        script = 'tell application "System Events" to sleep'
        success, _ = self._run_osascript(script)
        return success, "Going to sleep" if success else "Could not sleep"

    def _lock(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Lock the screen."""
        # Use the keyboard shortcut Cmd+Ctrl+Q
        script = """
        tell application "System Events"
            keystroke "q" using {command down, control down}
        end tell
        """
        success, _ = self._run_osascript(script)
        return success, "Screen locked" if success else "Could not lock screen"

    # Web commands
    def _search_web(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Search Google for a query."""
        query = cmd.params["query"]
        encoded_query = urllib.parse.quote(query)
        url = f"https://www.google.com/search?q={encoded_query}"
        success, _ = self._run_command(["open", url])
        return success, f"Searching for: {query}" if success else "Could not search"

    def _open_url(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Open a URL in the default browser."""
        url = cmd.params["url"]
        success, _ = self._run_command(["open", url])
        return success, f"Opening {url}" if success else f"Could not open {url}"

    def _open_website(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Open a known website."""
        website = cmd.params.get("website", "")
        url = cmd.params.get("url", "")
        success, _ = self._run_command(["open", url])
        return success, f"Opening {website}" if success else f"Could not open {website}"

    # Media commands
    def _play_pause(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Toggle play/pause for media."""
        script = """
        tell application "System Events"
            key code 49 using {}
        end tell
        """
        # Try using media key instead
        script = """
        tell application "System Events"
            key code 16 using {command down}
        end tell
        """
        # Better approach: use Spotify/Music directly or media key
        script_spotify = """
        if application "Spotify" is running then
            tell application "Spotify" to playpause
            return "Toggled Spotify"
        else if application "Music" is running then
            tell application "Music" to playpause
            return "Toggled Music"
        else
            tell application "System Events"
                key code 49
            end tell
            return "Toggled playback"
        end if
        """
        success, output = self._run_osascript(script_spotify)
        return success, output if success else "Could not toggle playback"

    def _next_track(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Skip to next track."""
        script = """
        if application "Spotify" is running then
            tell application "Spotify" to next track
            return "Next track (Spotify)"
        else if application "Music" is running then
            tell application "Music" to next track
            return "Next track (Music)"
        end if
        """
        success, output = self._run_osascript(script)
        return success, output if success else "Could not skip track"

    def _prev_track(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Go to previous track."""
        script = """
        if application "Spotify" is running then
            tell application "Spotify" to previous track
            return "Previous track (Spotify)"
        else if application "Music" is running then
            tell application "Music" to previous track
            return "Previous track (Music)"
        end if
        """
        success, output = self._run_osascript(script)
        return success, output if success else "Could not go to previous track"

    def _unknown(self, cmd: ParsedCommand) -> Tuple[bool, str]:
        """Handle unknown commands."""
        return False, f"Unknown command: {cmd.raw_text}"
