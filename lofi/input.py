"""Global hotkeys and hardware media keys.

Phantom-key rule: action binds match the key that fired ``on_press``, never
membership in ``pressed_keys``. That set is only used for modifier state.
Windows 11 often swallows ``on_release`` on focus changes.

Hardware media keys (including Bluetooth VK 250/251) are debounced at 0.3s.
"""

from __future__ import annotations

import time
from typing import Callable, Optional, Set

from pynput import keyboard

from lofi.config import AppConfig

MEDIA_DEBOUNCE_SECONDS = 0.3
DISCRETE_TTL_SECONDS = 0.4

MEDIA_VKS = (176, 177, 178, 179, 250, 251)


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

    def start(self) -> None:
        self._listener = keyboard.Listener(on_press=self._on_press, on_release=self._on_release)
        self._listener.start()

    def stop(self) -> None:
        if self._listener is not None:
            self._listener.stop()
            self._listener = None

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
            self._handle_media(key, vk)
            return

        if not self._modifier_pressed(config.mod_key):
            return

        playing = self._is_playing()

        if self._check_target_key(key, config.key_vol_up):
            if playing:
                self._dispatch("volume", 5)
            return
        if self._check_target_key(key, config.key_vol_down):
            if playing:
                self._dispatch("volume", -5)
            return

        if self._check_target_key(key, config.key_play) and "play" not in self._handled_discrete:
            self._dispatch("toggle")
            self._mark_discrete("play", now)
        elif self._check_target_key(key, config.key_prev) and "prev" not in self._handled_discrete:
            if playing:
                self._dispatch("prev")
            self._mark_discrete("prev", now)
        elif self._check_target_key(key, config.key_next) and "next" not in self._handled_discrete:
            if playing:
                self._dispatch("next")
            self._mark_discrete("next", now)
        elif (
            self._check_target_key(key, config.key_show_song)
            and "show_song" not in self._handled_discrete
        ):
            if playing:
                self._dispatch("show_song")
            self._mark_discrete("show_song", now)
        elif self._check_target_key(key, config.key_ignore) and "ignore" not in self._handled_discrete:
            if playing:
                self._dispatch("ignore")
            self._mark_discrete("ignore", now)

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
        if name == "alt":
            targets = (keyboard.Key.alt, keyboard.Key.alt_l, keyboard.Key.alt_r)
        elif name == "ctrl":
            targets = (keyboard.Key.ctrl, keyboard.Key.ctrl_l, keyboard.Key.ctrl_r)
        elif name == "shift":
            targets = (keyboard.Key.shift, keyboard.Key.shift_l, keyboard.Key.shift_r)
        else:
            return False
        return any(item in self._pressed_keys for item in targets)

    @staticmethod
    def _check_target_key(event_key: object, cfg_key: str) -> bool:
        target = cfg_key.lower()
        char = getattr(event_key, "char", None)
        if char and char.lower() == target:
            return True
        name = getattr(event_key, "name", None)
        if name and name.lower() == target:
            return True
        return False
