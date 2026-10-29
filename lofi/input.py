"""Global hotkeys and hardware media keys.

Phantom-key rule: action binds match the key that fired ``on_press``, never
membership in ``pressed_keys``. That set is only used for modifier state.
Windows 11 often swallows ``on_release`` on focus changes.

Hardware media keys (including Bluetooth VK 250/251) are debounced at 0.3s.
"""

from __future__ import annotations

import subprocess
import sys
import time
from typing import Callable, Optional, Set

from pynput import keyboard

from lofi.config import AppConfig

MEDIA_DEBOUNCE_SECONDS = 0.3
DISCRETE_TTL_SECONDS = 0.4

MEDIA_VKS = (176, 177, 178, 179, 250, 251)


def is_accessibility_trusted(prompt: bool = False) -> bool:
    """Check if the process has macOS Accessibility permissions, optionally prompting the OS dialog."""
    if sys.platform != "darwin":
        return True
    try:
        from ApplicationServices import AXIsProcessTrustedWithOptions, kAXTrustedCheckOptionPrompt

        if prompt:
            return bool(AXIsProcessTrustedWithOptions({kAXTrustedCheckOptionPrompt: True}))
        return bool(AXIsProcessTrustedWithOptions(None))
    except Exception:
        return False


def open_accessibility_settings() -> None:
    """Open macOS System Settings directly to Privacy & Security -> Accessibility."""
    if sys.platform == "darwin":
        try:
            subprocess.Popen(["open", "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"])
        except Exception:
            pass


class HotkeyController:
    """pynput listener that only enqueues work onto the Tk thread."""

    def __init__(
        self,
        get_config: Callable[[], AppConfig],
        dispatch: Callable[..., None],
        is_playing: Callable[[], bool],
    ) -> None:
        self._get_config = get_config
        self._dispatch = dispatch
        self._is_playing = is_playing
        self.is_binding = False
        self._pressed_keys: Set[object] = set()
        self._handled_discrete: Set[str] = set()
        self._discrete_until: dict = {}
        self._last_media_press = 0.0
        self._listener: Optional[keyboard.Listener] = None
        self._suppress_current = False
        self._suppressed_vks: Set[int] = set()

    def start(self) -> None:
        if sys.platform == "darwin":
            if not is_accessibility_trusted():
                # Ask macOS to show the system prompt to grant Accessibility permissions
                is_accessibility_trusted(prompt=True)
            self._listener = keyboard.Listener(
                on_press=self._on_press,
                on_release=self._on_release,
                darwin_intercept=self._darwin_intercept,
            )
        else:
            self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

    def _mark_suppressed(self, key: object) -> None:
        self._suppress_current = True
        vk = getattr(key, "vk", None)
        if vk is not None:
            self._suppressed_vks.add(vk)

    def _darwin_intercept(self, event_type: int, event: object) -> object:
        if sys.platform == "darwin":
            try:
                import Quartz

                if event_type == Quartz.kCGEventKeyDown:
                    if self._suppress_current:
                        self._suppress_current = False
                        return None
                elif event_type == Quartz.kCGEventKeyUp:
                    vk = Quartz.CGEventGetIntegerValueField(
                        event, Quartz.kCGKeyboardEventKeycode
                    )
                    if vk in self._suppressed_vks:
                        self._suppressed_vks.discard(vk)
                        return None
            except Exception:
                pass
        return event

    def _expire_discrete(self, now: float) -> None:
        expired = [name for name, until in self._discrete_until.items() if until <= now]
        for name in expired:
            self._handled_discrete.discard(name)
            self._discrete_until.pop(name, None)

    def _mark_discrete(self, name: str, now: float) -> None:
        self._handled_discrete.add(name)
        self._discrete_until[name] = now + DISCRETE_TTL_SECONDS

    def _on_press(self, key: object) -> None:
        if self.is_binding:
            return
        self._pressed_keys.add(key)

        config = self._get_config()
        vk = getattr(key, "vk", None)
        now = time.time()
        self._expire_discrete(now)

        is_media_key = key in (
            keyboard.Key.media_play_pause,
            keyboard.Key.media_next,
            keyboard.Key.media_previous,
        ) or vk in MEDIA_VKS

        if is_media_key:
            if not config.enable_hardware_keys:
                return
            if now - self._last_media_press < MEDIA_DEBOUNCE_SECONDS:
                return
            self._last_media_press = now
            self._mark_suppressed(key)
            self._handle_media(key, vk)
            return

        if not self._modifier_pressed(config.mod_key):
            return

        playing = self._is_playing()
        matched = False

        if self._check_target_key(key, config.key_vol_up):
            matched = True
            if playing:
                self._dispatch("volume", 5)
        elif self._check_target_key(key, config.key_vol_down):
            matched = True
            if playing:
                self._dispatch("volume", -5)
        elif self._check_target_key(key, config.key_play):
            matched = True
            if "play" not in self._handled_discrete:
                self._dispatch("toggle")
                self._mark_discrete("play", now)
        elif self._check_target_key(key, config.key_prev):
            matched = True
            if playing and "prev" not in self._handled_discrete:
                self._dispatch("prev")
                self._mark_discrete("prev", now)
        elif self._check_target_key(key, config.key_next):
            matched = True
            if playing and "next" not in self._handled_discrete:
                self._dispatch("next")
                self._mark_discrete("next", now)
        elif self._check_target_key(key, config.key_show_song):
            matched = True
            if playing and "show_song" not in self._handled_discrete:
                self._dispatch("show_song")
                self._mark_discrete("show_song", now)
        elif self._check_target_key(key, config.key_ignore):
            matched = True
            if playing and "ignore" not in self._handled_discrete:
                self._dispatch("ignore")
                self._mark_discrete("ignore", now)

        if matched:
            self._mark_suppressed(key)
            return


    def _handle_media(self, key: object, vk: Optional[int]) -> None:
        if key == keyboard.Key.media_play_pause or vk == 179:
            self._dispatch("toggle")
        elif vk == 250:
            self._dispatch("play")
        elif vk in (251, 178):
            self._dispatch("pause")
        elif key == keyboard.Key.media_next or vk == 176:
            if self._is_playing():
                self._dispatch("next")
        elif key == keyboard.Key.media_previous or vk == 177:
            if self._is_playing():
                self._dispatch("prev")

    def _on_release(self, key: object) -> None:
        if key in self._pressed_keys:
            self._pressed_keys.remove(key)
        vk = getattr(key, "vk", None)
        if vk is not None:
            self._suppressed_vks.discard(vk)

        config = self._get_config()
        if self._check_target_key(key, config.key_play):
            self._handled_discrete.discard("play")
            self._discrete_until.pop("play", None)
        elif self._check_target_key(key, config.key_prev):
            self._handled_discrete.discard("prev")
            self._discrete_until.pop("prev", None)
        elif self._check_target_key(key, config.key_next):
            self._handled_discrete.discard("next")
            self._discrete_until.pop("next", None)
        elif self._check_target_key(key, config.key_show_song):
            self._handled_discrete.discard("show_song")
            self._discrete_until.pop("show_song", None)
        elif self._check_target_key(key, config.key_ignore):
            self._handled_discrete.discard("ignore")
            self._discrete_until.pop("ignore", None)

    def _modifier_pressed(self, mod: str) -> bool:
        name = mod.lower()
        if name in ("alt", "option"):
            targets = (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
        elif name in ("ctrl", "control"):
            targets = (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        elif name == "shift":
            targets = (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        elif name in ("cmd", "command"):
            targets = (keyboard.Key.cmd, keyboard.Key.cmd_l, keyboard.Key.cmd_r)
        else:
            return False

        if sys.platform == "darwin":
            try:
                import Quartz

                flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateCombinedSessionState)
                if flags == 0:
                    flags = Quartz.CGEventSourceFlagsState(Quartz.kCGEventSourceStateHIDSystemState)

                if name in ("alt", "option"):
                    is_down = bool(flags & Quartz.kCGEventFlagMaskAlternate)
                elif name in ("cmd", "command"):
                    is_down = bool(flags & Quartz.kCGEventFlagMaskCommand)
                elif name in ("ctrl", "control"):
                    is_down = bool(flags & Quartz.kCGEventFlagMaskControl)
                elif name == "shift":
                    is_down = bool(flags & Quartz.kCGEventFlagMaskShift)
                else:
                    is_down = False

                if not is_down:
                    self._pressed_keys.difference_update(targets)
                return is_down
            except Exception:
                pass
        elif sys.platform == "win32":
            try:
                import ctypes

                vk = None
                if name in ("alt", "option"):
                    vk = 0x12
                elif name in ("ctrl", "control"):
                    vk = 0x11
                elif name == "shift":
                    vk = 0x10
                if vk is not None:
                    is_down = bool(ctypes.windll.user32.GetAsyncKeyState(vk) & 0x8000)
                    if not is_down:
                        self._pressed_keys.difference_update(targets)
                    return is_down
            except Exception:
                pass

        return any(item in self._pressed_keys for item in targets)

    @staticmethod
    def _check_target_key(event_key: object, cfg_key: str) -> bool:
        target = cfg_key.lower().strip()
        char = getattr(event_key, "char", None)
        if char and char.lower() == target:
            return True
        name = getattr(event_key, "name", None)
        if name and name.lower() == target:
            return True
        if sys.platform == "darwin":
            vk = getattr(event_key, "vk", None)
            if vk is not None:
                try:
                    import pynput.keyboard._darwin as darwin_kb

                    sym = darwin_kb.SYMBOLS.get(vk)
                    if sym and sym.lower() == target:
                        return True
                    if target in ("space", " ") and sym in (" ", "space"):
                        return True
                except Exception:
                    pass
        return False

