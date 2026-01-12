"""Combined hotkey manager for multiple hotkey sets."""

from pynput import keyboard
from typing import Callable, Optional, Set, Dict
import threading


class CombinedHotkeyManager:
    """Manages multiple hotkeys with a single keyboard listener."""

    def __init__(self):
        self._hotkeys: Dict[str, dict] = {}  # name -> {keys, mode, on_activate, on_deactivate, is_active}
        self._pressed_keys: Set[str] = set()
        self._listener: Optional[keyboard.Listener] = None
        self._lock = threading.Lock()

    def add_hotkey(
        self,
        name: str,
        hotkey: Set[str],
        activation_mode: str = "hold",
        on_activate: Optional[Callable[[], None]] = None,
        on_deactivate: Optional[Callable[[], None]] = None,
    ):
        """Add a hotkey configuration."""
        self._hotkeys[name] = {
            "keys": self._normalize_hotkey(hotkey),
            "mode": activation_mode,
            "on_activate": on_activate,
            "on_deactivate": on_deactivate,
            "is_active": False,
        }

    def _normalize_hotkey(self, hotkey: Set[str]) -> Set[str]:
        """Normalize hotkey names."""
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
            "shift_r": "shift_r",
            "shift_l": "shift_l",
            "space": "space",
            "esc": "esc",
            "escape": "esc",
            "fn": "fn",
        }
        for key in hotkey:
            key_lower = key.lower()
            normalized.add(key_map.get(key_lower, key_lower))
        return normalized

    def _get_key_name(self, key) -> Optional[str]:
        """Get normalized key name from pynput key object."""
        try:
            if hasattr(key, "name"):
                name = key.name.lower()
                if name in ("cmd", "cmd_l", "cmd_r"):
                    return "cmd"
                elif name == "ctrl_r":
                    return "ctrl_r"
                elif name in ("ctrl", "ctrl_l"):
                    return "ctrl"
                elif name == "alt_r":
                    return "alt_r"
                elif name in ("alt", "alt_l", "alt_gr"):
                    return "alt"
                elif name == "shift_r":
                    return "shift_r"
                elif name == "shift_l":
                    return "shift_l"
                elif name == "shift":
                    return "shift"
                elif name == "caps_lock":
                    return "caps_lock"
                elif name == "space":
                    return "space"
                elif name in ("esc", "escape"):
                    return "esc"
                elif name in ("fn", "function"):
                    return "fn"
                return name
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

            # Check each hotkey
            for name, config in self._hotkeys.items():
                if config["keys"].issubset(self._pressed_keys):
                    if config["mode"] == "hold":
                        if not config["is_active"]:
                            config["is_active"] = True
                            if config["on_activate"]:
                                config["on_activate"]()
                    elif config["mode"] == "toggle":
                        if not config["is_active"]:
                            config["is_active"] = True
                            if config["on_activate"]:
                                config["on_activate"]()
                        else:
                            config["is_active"] = False
                            if config["on_deactivate"]:
                                config["on_deactivate"]()

    def _on_release(self, key) -> None:
        """Handle key release events."""
        key_name = self._get_key_name(key)
        if key_name is None:
            return

        with self._lock:
            # For hold mode: deactivate when any hotkey key is released
            for name, config in self._hotkeys.items():
                if config["mode"] == "hold" and config["is_active"]:
                    if key_name in config["keys"]:
                        config["is_active"] = False
                        if config["on_deactivate"]:
                            config["on_deactivate"]()

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
        for config in self._hotkeys.values():
            config["is_active"] = False

    def set_activation_mode(self, name: str, mode: str) -> None:
        """Change the activation mode for a hotkey."""
        if name in self._hotkeys and mode in ("hold", "toggle"):
            self._hotkeys[name]["mode"] = mode
