"""Global hotkey management using pynput."""

from pynput import keyboard
from typing import Callable, Optional, Set
import threading


class HotkeyManager:
    """Manages global hotkey detection for recording activation."""

    def __init__(
        self,
        hotkey: Set[str],
        activation_mode: str = "hold",
        on_activate: Optional[Callable[[], None]] = None,
        on_deactivate: Optional[Callable[[], None]] = None,
    ):
        """
        Initialize the hotkey manager.

        Args:
            hotkey: Set of keys that form the hotkey (e.g., {"cmd", "shift", "space"})
            activation_mode: "hold" for press-and-hold, "toggle" for toggle mode
            on_activate: Callback when recording should start
            on_deactivate: Callback when recording should stop
        """
        self.hotkey = self._normalize_hotkey(hotkey)
        self.activation_mode = activation_mode
        self.on_activate = on_activate
        self.on_deactivate = on_deactivate

        self._pressed_keys: Set[str] = set()
        self._is_active = False
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def _normalize_hotkey(self, hotkey: Set[str]) -> Set[str]:
        """Normalize hotkey names to pynput format."""
        normalized = set()
        key_map = {
            "cmd": "cmd",
            "command": "cmd",
            "ctrl": "ctrl",
            "control": "ctrl",
            "alt": "alt",
            "option": "alt",
            "opt": "alt",
            "shift": "shift",
            "space": "space",
        }
        for key in hotkey:
            key_lower = key.lower()
            normalized.add(key_map.get(key_lower, key_lower))
        return normalized

    def _get_key_name(self, key) -> Optional[str]:
        """Get normalized key name from pynput key object."""
        try:
            # Handle special keys
            if hasattr(key, "name"):
                name = key.name.lower()
                if name in ("cmd", "cmd_l", "cmd_r"):
                    return "cmd"
                elif name in ("ctrl", "ctrl_l", "ctrl_r"):
                    return "ctrl"
                elif name in ("alt", "alt_l", "alt_r", "alt_gr"):
                    return "alt"
                elif name in ("shift", "shift_l", "shift_r"):
                    return "shift"
                elif name == "space":
                    return "space"
                return name
            # Handle regular character keys
            elif hasattr(key, "char") and key.char:
                return key.char.lower()
        except AttributeError:
            pass
        return None

    def _on_press(self, key) -> None:
        """Handle key press events."""
        key_name = self._get_key_name(key)
        if key_name is None:
            return

        with self._lock:
            self._pressed_keys.add(key_name)

            # Check if hotkey combination is pressed
            if self.hotkey.issubset(self._pressed_keys):
                if self.activation_mode == "hold":
                    # Hold mode: activate on press
                    if not self._is_active:
                        self._is_active = True
                        if self.on_activate:
                            self.on_activate()
                elif self.activation_mode == "toggle":
                    # Toggle mode: toggle on press
                    if not self._is_active:
                        self._is_active = True
                        if self.on_activate:
                            self.on_activate()
                    else:
                        self._is_active = False
                        if self.on_deactivate:
                            self.on_deactivate()

    def _on_release(self, key) -> None:
        """Handle key release events."""
        key_name = self._get_key_name(key)
        if key_name is None:
            return

        with self._lock:
            # For hold mode: deactivate when any hotkey key is released
            if self.activation_mode == "hold" and self._is_active:
                if key_name in self.hotkey:
                    self._is_active = False
                    if self.on_deactivate:
                        self.on_deactivate()

            self._pressed_keys.discard(key_name)

    def start(self) -> None:
        """Start listening for hotkeys."""
        if self._listener is not None:
            return

        self._listener = keyboard.Listener(
            on_press=self._on_press,
            on_release=self._on_release,
        )
        self._listener.start()

    def stop(self) -> None:
        """Stop listening for hotkeys."""
        if self._listener:
            self._listener.stop()
            self._listener = None
        self._pressed_keys.clear()
        self._is_active = False

    def is_active(self) -> bool:
        """Check if recording is currently active."""
        return self._is_active

    def set_activation_mode(self, mode: str) -> None:
        """Change the activation mode."""
        if mode in ("hold", "toggle"):
            self.activation_mode = mode
