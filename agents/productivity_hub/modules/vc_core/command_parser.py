"""Command parser for voice commands."""

import re
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum


class CommandType(Enum):
    """Types of commands."""
    OPEN_APP = "open_app"
    CLOSE_APP = "close_app"
    SWITCH_APP = "switch_app"
    MINIMIZE_APP = "minimize_app"

    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    VOLUME_MUTE = "volume_mute"
    VOLUME_SET = "volume_set"

    BRIGHTNESS_UP = "brightness_up"
    BRIGHTNESS_DOWN = "brightness_down"

    SCREENSHOT = "screenshot"
    SCREENSHOT_AREA = "screenshot_area"

    SLEEP = "sleep"
    LOCK = "lock"

    SEARCH_WEB = "search_web"
    OPEN_URL = "open_url"
    OPEN_WEBSITE = "open_website"

    PLAY_PAUSE = "play_pause"
    NEXT_TRACK = "next_track"
    PREV_TRACK = "prev_track"

    UNKNOWN = "unknown"


@dataclass
class ParsedCommand:
    """Parsed command result."""
    command_type: CommandType
    params: Dict[str, Any]
    raw_text: str
    confidence: float = 1.0


class CommandParser:
    """Parses voice commands into structured actions."""

    def __init__(self, app_aliases: Dict[str, str], website_shortcuts: Dict[str, str]):
        self.app_aliases = {k.lower(): v for k, v in app_aliases.items()}
        self.website_shortcuts = {k.lower(): v for k, v in website_shortcuts.items()}

        # Command patterns (order matters - more specific first)
        self.patterns = [
            # Web commands (check first to catch "go to youtube" etc.)
            (r"(?:go to|open)\s+(?:the\s+)?(?:website\s+)?(?:https?://)?(\S+\.(?:com|org|net|io|dev|ai|co|app)(?:/\S*)?)", self._parse_open_url),

            # App commands
            (r"(?:open|launch|start|run)\s+(.+)", self._parse_open_app),
            (r"(?:close|quit|exit|kill)\s+(.+)", self._parse_close_app),
            (r"(?:switch to|focus on|focus)\s+(.+)", self._parse_switch_app),
            (r"(?:minimize|minimise|hide)\s+(.+)", self._parse_minimize_app),
            (r"minimize$", self._parse_minimize_current),

            # Volume commands
            (r"(?:volume|sound)\s+(?:up|increase|louder|raise)", self._parse_volume_up),
            (r"(?:volume|sound)\s+(?:down|decrease|lower|reduce)", self._parse_volume_down),
            (r"(?:mute|unmute|toggle mute)", self._parse_volume_mute),
            (r"(?:set\s+)?(?:volume|sound)\s+(?:to\s+)?(\d+)", self._parse_volume_set),
            (r"(?:turn|make)\s+(?:it\s+)?(?:up|louder)", self._parse_volume_up),
            (r"(?:turn|make)\s+(?:it\s+)?(?:down|quieter)", self._parse_volume_down),

            # Brightness commands
            (r"(?:brightness|screen)\s+(?:up|increase|brighter)", self._parse_brightness_up),
            (r"(?:brightness|screen)\s+(?:down|decrease|dimmer|darker)", self._parse_brightness_down),

            # Screenshot commands
            (r"(?:take\s+)?(?:a\s+)?screenshot(?:\s+of\s+)?(?:area|selection|region)", self._parse_screenshot_area),
            (r"(?:take\s+)?(?:a\s+)?screenshot", self._parse_screenshot),
            (r"capture\s+(?:screen|display)", self._parse_screenshot),

            # System commands
            (r"(?:go to\s+)?sleep", self._parse_sleep),
            (r"lock\s+(?:screen|computer|mac)", self._parse_lock),
            (r"lock$", self._parse_lock),

            # Media commands
            (r"(?:play|pause|play pause|toggle play)", self._parse_play_pause),
            (r"(?:next|skip)\s*(?:track|song)?", self._parse_next_track),
            (r"(?:previous|prev|back)\s*(?:track|song)?", self._parse_prev_track),

            # Web commands
            (r"search\s+(?:for\s+)?(.+?)(?:\s+on\s+google)?$", self._parse_search),
            (r"google\s+(.+)", self._parse_search),
            (r"(?:go to)\s+(.+)", self._parse_open_website),  # "go to X" - check if it's a website shortcut
        ]

    def parse(self, text: str) -> ParsedCommand:
        """Parse voice command text into structured command."""
        # Normalize text
        text = text.lower().strip()
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace

        # Try each pattern
        for pattern, handler in self.patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                result = handler(match, text)
                if result:
                    return result

        # Unknown command
        return ParsedCommand(
            command_type=CommandType.UNKNOWN,
            params={"text": text},
            raw_text=text,
            confidence=0.0
        )

    def _parse_open_app(self, match: re.Match, text: str) -> Optional[ParsedCommand]:
        """Parse open app command."""
        app_name = match.group(1).strip().lower()

        # Check if it's actually a website
        if app_name in self.website_shortcuts:
            return ParsedCommand(
                command_type=CommandType.OPEN_WEBSITE,
                params={"website": app_name, "url": self.website_shortcuts[app_name]},
                raw_text=text
            )

        # Resolve app alias
        resolved_name = self.app_aliases.get(app_name, app_name.title())

        return ParsedCommand(
            command_type=CommandType.OPEN_APP,
            params={"app_name": resolved_name, "spoken_name": app_name},
            raw_text=text
        )

    def _parse_close_app(self, match: re.Match, text: str) -> Optional[ParsedCommand]:
        """Parse close app command."""
        app_name = match.group(1).strip().lower()
        resolved_name = self.app_aliases.get(app_name, app_name.title())

        return ParsedCommand(
            command_type=CommandType.CLOSE_APP,
            params={"app_name": resolved_name, "spoken_name": app_name},
            raw_text=text
        )

    def _parse_switch_app(self, match: re.Match, text: str) -> Optional[ParsedCommand]:
        """Parse switch app command."""
        app_name = match.group(1).strip().lower()
        resolved_name = self.app_aliases.get(app_name, app_name.title())

        return ParsedCommand(
            command_type=CommandType.SWITCH_APP,
            params={"app_name": resolved_name, "spoken_name": app_name},
            raw_text=text
        )

    def _parse_minimize_app(self, match: re.Match, text: str) -> Optional[ParsedCommand]:
        """Parse minimize app command."""
        app_name = match.group(1).strip().lower()
        resolved_name = self.app_aliases.get(app_name, app_name.title())

        return ParsedCommand(
            command_type=CommandType.MINIMIZE_APP,
            params={"app_name": resolved_name, "spoken_name": app_name},
            raw_text=text
        )

    def _parse_minimize_current(self, match: re.Match, text: str) -> ParsedCommand:
        """Parse minimize current window command."""
        return ParsedCommand(
            command_type=CommandType.MINIMIZE_APP,
            params={"app_name": None, "current": True},
            raw_text=text
        )

    def _parse_volume_up(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.VOLUME_UP, {}, text)

    def _parse_volume_down(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.VOLUME_DOWN, {}, text)

    def _parse_volume_mute(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.VOLUME_MUTE, {}, text)

    def _parse_volume_set(self, match: re.Match, text: str) -> ParsedCommand:
        level = int(match.group(1))
        level = max(0, min(100, level))  # Clamp to 0-100
        return ParsedCommand(CommandType.VOLUME_SET, {"level": level}, text)

    def _parse_brightness_up(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.BRIGHTNESS_UP, {}, text)

    def _parse_brightness_down(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.BRIGHTNESS_DOWN, {}, text)

    def _parse_screenshot(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.SCREENSHOT, {}, text)

    def _parse_screenshot_area(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.SCREENSHOT_AREA, {}, text)

    def _parse_sleep(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.SLEEP, {}, text)

    def _parse_lock(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.LOCK, {}, text)

    def _parse_play_pause(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.PLAY_PAUSE, {}, text)

    def _parse_next_track(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.NEXT_TRACK, {}, text)

    def _parse_prev_track(self, match: re.Match, text: str) -> ParsedCommand:
        return ParsedCommand(CommandType.PREV_TRACK, {}, text)

    def _parse_search(self, match: re.Match, text: str) -> ParsedCommand:
        query = match.group(1).strip()
        return ParsedCommand(
            command_type=CommandType.SEARCH_WEB,
            params={"query": query},
            raw_text=text
        )

    def _parse_open_url(self, match: re.Match, text: str) -> ParsedCommand:
        url = match.group(1).strip()
        if not url.startswith("http"):
            url = "https://" + url
        return ParsedCommand(
            command_type=CommandType.OPEN_URL,
            params={"url": url},
            raw_text=text
        )

    def _parse_open_website(self, match: re.Match, text: str) -> Optional[ParsedCommand]:
        site_name = match.group(1).strip().lower()

        # Check shortcuts
        if site_name in self.website_shortcuts:
            return ParsedCommand(
                command_type=CommandType.OPEN_WEBSITE,
                params={"website": site_name, "url": self.website_shortcuts[site_name]},
                raw_text=text
            )

        # Check if it's an app instead
        if site_name in self.app_aliases:
            return ParsedCommand(
                command_type=CommandType.OPEN_APP,
                params={"app_name": self.app_aliases[site_name], "spoken_name": site_name},
                raw_text=text
            )

        # Try as URL
        if "." in site_name:
            url = f"https://{site_name}" if not site_name.startswith("http") else site_name
            return ParsedCommand(
                command_type=CommandType.OPEN_URL,
                params={"url": url},
                raw_text=text
            )

        # Unknown website, try Google search
        return ParsedCommand(
            command_type=CommandType.SEARCH_WEB,
            params={"query": site_name},
            raw_text=text
        )
