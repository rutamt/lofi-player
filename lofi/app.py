"""Composition root: Tk loop, playback, HUD, hotkeys, tray, and monitors."""

from __future__ import annotations

import os
import sys
import winreg
from typing import Optional

import customtkinter as ctk

from lofi.config import AppConfig, load_config, save_config
from lofi.devices import get_active_audio_devices
from lofi.engine import Player
from lofi.hud import Hud
from lofi.input import HotkeyController
from lofi.settings import SettingsController
from lofi.themes import get_theme
from lofi.tray import Tray


def enable_autostart() -> None:
    """Write the frozen executable into the current-user Run key."""
    if not getattr(sys, "frozen", False):
        return
    exe_path = sys.executable
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.SetValueEx(key, "LoFiHUD", 0, winreg.REG_SZ, exe_path)
        winreg.CloseKey(key)
    except OSError:
        pass


def ensure_music_dir(path: str) -> None:
    if os.path.exists(path):
        return
    try:
        os.makedirs(path)
    except OSError:
        pass


class App:
    """Owns shared state and marshals all engine/UI work onto the Tk thread."""

    def __init__(self) -> None:
        enable_autostart()
        self.config = load_config()
        ensure_music_dir(self.config.music_dir)

        theme = get_theme(self.config.theme)
        ctk.set_appearance_mode(theme.appearance)

        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        self.player = Player(volume=self.config.volume)
        self.player.load_library(self.config.music_dir)

        self.hud = Hud(self.root)
        self.hud.apply_theme(theme)

        self._last_played_mrl: Optional[str] = None
        self._was_device_present = False

        self.hotkeys = HotkeyController(
            get_config=lambda: self.config,
            dispatch=self.dispatch,
            is_playing=lambda: self.player.is_playing,
        )
        self.settings = SettingsController(
            self.root,
            get_config=lambda: self.config,
            save_config=self.apply_config,
            get_devices=get_active_audio_devices,
            set_binding=self._set_binding,
        )
        self.tray = Tray(
            on_settings=lambda: self.root.after_idle(self.settings.open),
            on_toggle=lambda: self.root.after_idle(self.toggle_audio),
            on_next=lambda: self.root.after_idle(self.next_track),
            on_exit=self._on_exit,
        )

        self.hotkeys.start()
        self.tray.start()
        self.root.after(1000, self._track_monitor)
        self.root.after(2000, self._device_monitor)
        if not self.player.available:
            self.root.after(
                400,
                lambda: self.hud.show("VLC not found — install 64-bit VLC", self.config, 5000),
            )

    def dispatch(self, action: str, *args: object) -> None:
        self.root.after(0, self._run_action, action, *args)

    def _run_action(self, action: str, *args: object) -> None:
        if action == "toggle":
            self.toggle_audio()
        elif action == "play":
            self.force_play()
        elif action == "pause":
            self.force_pause()
        elif action == "next":
            self.next_track()
        elif action == "prev":
            self.prev_track()
        elif action == "show_song":
            self.show_current_song()
        elif action == "ignore":
            self.ignore_current_song()
        elif action == "volume" and args:
            self.change_volume(int(args[0]))

    def _set_binding(self, value: bool) -> None:
        self.hotkeys.is_binding = value

    def toast(
        self,
        message: str,
        duration: Optional[int] = None,
        *,
        actions: bool = False,
        badge: Optional[str] = None,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> None:
        if actions and not self.config.show_actions:
            return
        self.hud.show(
            message,
            self.config,
            duration,
            badge=badge,
            title=title,
            icon=icon,
            progress=progress,
        )

    def force_play(self) -> None:
        if self.player.play():
            self.toast("▶ Resumed", actions=True)

    def force_pause(self) -> None:
        if self.player.pause():
            self.toast("⏸ Paused", actions=True)

    def toggle_audio(self) -> None:
        result = self.player.toggle()
        if result == "empty":
            self.toast("Folder Empty: Add MP3s", actions=True)
        elif result == "pause":
            self.toast("⏸ Paused", actions=True)
        elif result == "play":
            self.toast("▶ Resumed", actions=True)

    def next_track(self) -> None:
        self.player.next()

    def prev_track(self) -> None:
        self.player.previous()

    def show_current_song(self) -> None:
        name = self.player.clean_name()
        if name:
            self.hud.show("🎵 {}".format(name), self.config, self.config.hud_song_timeout)
        else:
            self.hud.show("No Song Playing", self.config)

    def ignore_current_song(self) -> None:
        song_name = self.player.ignore_current(self.config.music_dir)
        if song_name:
            self.hud.show(
                "🗑 Removed: {}".format(song_name),
                self.config,
                self.config.hud_song_timeout,
            )
        else:
            self.hud.show("❌ Failed to remove file", self.config)

    def change_volume(self, delta: int) -> None:
        self.config.volume = self.player.set_volume(self.config.volume + delta)
        self.toast(
            "🔊 Volume: {}%".format(self.config.volume),
            actions=True,
            badge="VOLUME",
            icon="🔊",
            progress=self.config.volume,
        )
        save_config(self.config)

    def apply_config(self, new_config: AppConfig) -> None:
        music_dir_changed = new_config.music_dir != self.config.music_dir
        self.config = new_config
        save_config(self.config)
        theme = get_theme(self.config.theme)
        ctk.set_appearance_mode(theme.appearance)
        self.hud.apply_theme(theme)
        self.player.set_volume(self.config.volume)
        if music_dir_changed:
            ensure_music_dir(self.config.music_dir)
            self.player.load_library(self.config.music_dir)
            self._last_played_mrl = None
        self.toast("Settings Saved!")

    def _track_monitor(self) -> None:
        if self.player.is_media_playing() and self.config.show_now_playing:
            mrl = self.player.current_mrl()
            if mrl and mrl != self._last_played_mrl:
                self._last_played_mrl = mrl
                song_name = self.player.clean_name()
                if song_name:
                    self.hud.show(
                        "🎵 Now Playing: {}".format(song_name),
                        self.config,
                        self.config.hud_song_timeout,
                    )
        self.root.after(1000, self._track_monitor)

    def _device_monitor(self) -> None:
        target = self.config.autopause_device
        if target != "Disabled" and self.player.is_playing:
            active_names = get_active_audio_devices()
            if target in active_names:
                self._was_device_present = True
            elif self._was_device_present:
                self.force_pause()
                self.hud.show("⏸ Auto-Paused (Device Disconnected)", self.config, 5000)
                self._was_device_present = False
        self.root.after(2000, self._device_monitor)

    def _on_exit(self, *_args: object) -> None:
        self.hotkeys.stop()
        self.player.stop()
        self.tray.stop()
        os._exit(0)

    def run(self) -> None:
        self.root.mainloop()
