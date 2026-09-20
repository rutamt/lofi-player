"""Composition root: Tk loop, playback, HUD, hotkeys, tray, and monitors."""

from __future__ import annotations

import os
import subprocess
import sys
import winreg
from typing import Optional

import customtkinter as ctk

from lofi.config import AppConfig, load_config, save_config
from lofi.devices import get_active_audio_devices
from lofi.engine import Player
from lofi.hud import Hud
from lofi.input import HotkeyController
from lofi.paths import icon_path
from lofi.settings import SettingsController
from lofi.themes import get_theme
from lofi.tray import Tray


def _get_target_executable() -> str:
    return sys.executable


def _create_shortcut(target_exe: str, lnk_path: str, icon: Optional[str] = None) -> None:
    """Create a Windows .lnk shortcut cleanly without showing a console window."""
    try:
        os.makedirs(os.path.dirname(lnk_path), exist_ok=True)
        ps_cmd = (
            f'$ws = New-Object -ComObject WScript.Shell; '
            f'$s = $ws.CreateShortcut("{lnk_path}"); '
            f'$s.TargetPath = "{target_exe}"; '
        )
        if not getattr(sys, "frozen", False):
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lofi_hud.py"))
            ps_cmd += f'$s.Arguments = "`"{script_path}`""; '
        if icon and os.path.exists(icon):
            ps_cmd += f'$s.IconLocation = "{icon},0"; '
        ps_cmd += '$s.Save()'

        subprocess.run(
            ["powershell", "-NoProfile", "-Command", ps_cmd],
            check=False,
            creationflags=0x08000000,  # CREATE_NO_WINDOW
        )
    except Exception:
        pass


def install_start_menu_shortcut() -> None:
    """Register in Windows Start Menu so LoFi HUD is indexed by Windows Search."""
    try:
        start_menu = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        lnk_path = os.path.join(start_menu, "LoFi HUD.lnk")
        _create_shortcut(_get_target_executable(), lnk_path, icon_path())
    except Exception:
        pass


def sync_autostart(enabled: bool) -> None:
    """Configure autostart via the Windows Startup folder to eliminate the 2-minute delay."""
    try:
        startup_dir = os.path.join(
            os.environ.get("APPDATA", ""),
            r"Microsoft\Windows\Start Menu\Programs\Startup",
        )
        startup_lnk = os.path.join(startup_dir, "LoFi HUD.lnk")

        # Clean up legacy Run registry key to prevent delayed duplicate execution
        try:
            key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
                winreg.DeleteValue(key, "LoFiHUD")
        except OSError:
            pass

        if enabled:
            _create_shortcut(_get_target_executable(), startup_lnk, icon_path())
        else:
            if os.path.exists(startup_lnk):
                os.remove(startup_lnk)
    except Exception:
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
        self.config = load_config()
        ensure_music_dir(self.config.music_dir)
        install_start_menu_shortcut()
        sync_autostart(self.config.autostart)

        theme = get_theme(self.config.theme)

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
            on_open_folder=lambda: self.root.after_idle(self.open_music_folder),
            on_exit=self._on_exit,
        )

        self.hotkeys.start()
        self.tray.start()
        self._update_tray_title()
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
            self._update_tray_title()

    def force_pause(self) -> None:
        if self.player.pause():
            self.toast("⏸ Paused", actions=True)
            self._update_tray_title()

    def toggle_audio(self) -> None:
        result = self.player.toggle()
        if result == "empty":
            self.toast("Folder Empty: Add MP3s", actions=True)
            self.open_music_folder()
        elif result == "pause":
            self.toast("⏸ Paused", actions=True)
            self._update_tray_title()
        elif result == "play":
            self.toast("▶ Resumed", actions=True)
            self._update_tray_title()

    def next_track(self) -> None:
        self.player.next()

    def prev_track(self) -> None:
        self.player.previous()

    def open_music_folder(self) -> None:
        try:
            if not os.path.exists(self.config.music_dir):
                ensure_music_dir(self.config.music_dir)
            os.startfile(self.config.music_dir)
        except Exception:
            pass

    def _update_tray_title(self) -> None:
        song_name = self.player.clean_name()
        if self.player.is_playing:
            title = f"LoFi HUD — ▶ {song_name}" if song_name else "LoFi HUD — Playing"
        elif song_name:
            title = f"LoFi HUD — ⏸ {song_name}"
        else:
            title = "LoFi HUD — Idle"
        self.tray.set_title(title)

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
        sync_autostart(self.config.autostart)
        theme = get_theme(self.config.theme)
        self.hud.apply_theme(theme)
        self.player.set_volume(self.config.volume)
        if music_dir_changed:
            ensure_music_dir(self.config.music_dir)
            self.player.load_library(self.config.music_dir)
            self._last_played_mrl = None
        self.toast("Settings Saved!")

    def _track_monitor(self) -> None:
        if self.player.is_media_playing():
            mrl = self.player.current_mrl()
            if mrl and mrl != self._last_played_mrl:
                self._last_played_mrl = mrl
                song_name = self.player.clean_name()
                if song_name and self.config.show_now_playing:
                    self.hud.show(
                        "🎵 Now Playing: {}".format(song_name),
                        self.config,
                        self.config.hud_song_timeout,
                    )
                self._update_tray_title()
        self.root.after(1000, self._track_monitor)

    def _device_monitor(self) -> None:
        interval = 2000
        target = self.config.autopause_device
        if target == "Disabled":
            # Disabled: reduce polling to save CPU cycles
            interval = 5000
        elif not self.player.is_playing:
            # Paused/idle: device disconnection does not affect active audio
            interval = 4000
        else:
            # Actively playing: check device quickly for responsive auto-pause
            interval = 1500
            active_names = get_active_audio_devices()
            if target in active_names:
                self._was_device_present = True
            elif self._was_device_present:
                self.force_pause()
                self.hud.show("⏸ Auto-Paused (Device Disconnected)", self.config, 5000)
                self._was_device_present = False
        self.root.after(interval, self._device_monitor)

    def _on_exit(self, *_args: object) -> None:
        self.hotkeys.stop()
        self.player.stop()
        self.tray.stop()
        os._exit(0)

    def run(self) -> None:
        self.root.mainloop()
