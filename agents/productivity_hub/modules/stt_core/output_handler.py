"""Output handling - clipboard and keyboard simulation."""

import pyperclip
from pynput.keyboard import Controller, Key
import time
from typing import Literal


class OutputHandler:
    """Handles output of transcribed text to clipboard and/or keyboard."""

    def __init__(
        self,
        mode: Literal["clipboard", "type", "both"] = "both",
        typing_delay: float = 0.01,
    ):
        """
        Initialize the output handler.

        Args:
            mode: Output mode - "clipboard", "type", or "both"
            typing_delay: Delay between keystrokes when typing (seconds)
        """
        self.mode = mode
        self.typing_delay = typing_delay
        self._keyboard = Controller()

    def output(self, text: str) -> None:
        """
        Output the transcribed text.

        Args:
            text: The text to output
        """
        if not text:
            return

        if self.mode in ("clipboard", "both"):
            self._copy_to_clipboard(text)

        if self.mode in ("type", "both"):
            self._type_text(text)

    def _copy_to_clipboard(self, text: str) -> None:
        """Copy text to clipboard."""
        try:
            pyperclip.copy(text)
        except Exception as e:
            print(f"Failed to copy to clipboard: {e}")

    def _type_text(self, text: str) -> None:
        """Simulate keyboard typing at the currently focused cursor position."""
        try:
            # Delay to ensure user has focused on their target application
            # after releasing the hotkey
            time.sleep(0.3)

            for char in text:
                if char == "\n":
                    self._keyboard.press(Key.enter)
                    self._keyboard.release(Key.enter)
                elif char == "\t":
                    self._keyboard.press(Key.tab)
                    self._keyboard.release(Key.tab)
                else:
                    self._keyboard.type(char)

                if self.typing_delay > 0:
                    time.sleep(self.typing_delay)

        except Exception as e:
            print(f"Failed to type text: {e}")

    def set_mode(self, mode: Literal["clipboard", "type", "both"]) -> None:
        """Change the output mode."""
        self.mode = mode

    def set_typing_delay(self, delay: float) -> None:
        """Change the typing delay."""
        self.typing_delay = max(0, delay)
