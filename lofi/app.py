"""Composition root: Tk loop, playback, HUD, hotkeys, tray, and monitors."""

from __future__ import annotations

import os
import queue
import subprocess
import sys
from typing import Any, Optional

import customtkinter as ctk

from lofi.config import AppConfig, load_config, save_config
from lofi.devices import get_active_audio_devices
from lofi.engine import Player
from lofi.hud import Hud
from lofi.input import HotkeyController
from lofi.instance import SingleInstance
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
    if sys.platform != "win32":
        return
    try:
        start_menu = os.path.join(os.environ.get("APPDATA", ""), r"Microsoft\Windows\Start Menu\Programs")
        lnk_path = os.path.join(start_menu, "LoFi HUD.lnk")
        _create_shortcut(_get_target_executable(), lnk_path, icon_path())
    except Exception:
        pass


def _get_mac_launch_args() -> list[str]:
    app_path = "/Applications/LoFi HUD.app"
    if os.path.exists(app_path):
        return ["/usr/bin/open", "-a", app_path]
    if getattr(sys, "frozen", False):
        return [sys.executable]
    script = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "lofi_hud.py"))
    return [sys.executable, script]


def sync_autostart(enabled: bool) -> None:
    """Configure autostart on Windows (Startup folder) or macOS (LaunchAgent)."""
    if sys.platform == "win32":
        try:
            import winreg

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
    elif sys.platform == "darwin":
        try:
            agent_dir = os.path.expanduser("~/Library/LaunchAgents")
            os.makedirs(agent_dir, exist_ok=True)
            plist_path = os.path.join(agent_dir, "com.rutamt.lofihud.plist")
            if enabled:
                args = _get_mac_launch_args()
                args_xml = "\n".join(f"        <string>{a}</string>" for a in args)
                plist_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.rutamt.lofihud</string>
    <key>ProgramArguments</key>
    <array>
{args_xml}
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>ProcessType</key>
    <string>Interactive</string>
</dict>
</plist>
"""
                with open(plist_path, "w", encoding="utf-8") as f:
                    f.write(plist_content)
            else:
                if os.path.exists(plist_path):
                    os.remove(plist_path)
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

    def __init__(self, single_instance: Optional[SingleInstance] = None) -> None:
        self._single_instance = single_instance
        self.config = load_config()
        ensure_music_dir(self.config.music_dir)
        install_start_menu_shortcut()
        sync_autostart(self.config.autostart)

        theme = get_theme(self.config.theme)

        self.root = ctk.CTk()
        self.root.withdraw()
        self.root.protocol("WM_DELETE_WINDOW", lambda: None)

        self._track_monitor_timer: Optional[str] = None
        self._device_monitor_timer: Optional[str] = None

        self._action_queue: queue.Queue = queue.Queue()
        self.root.bind("<<ActionQueue>>", lambda _event: self._process_action_queue())

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
            on_rescan=self.rescan_library,
        )
        self.tray = Tray(
            on_settings=lambda: self.dispatch(self.settings.open),
            on_toggle=lambda: self.dispatch(self.toggle_audio),
            on_next=lambda: self.dispatch(self.next_track),
            on_rescan=lambda: self.dispatch(self.rescan_library),
            on_open_folder=lambda: self.dispatch(self.open_music_folder),
            on_exit=lambda: self.dispatch(self._on_exit),
        )

        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage

                ns_img = NSImage.alloc().initWithContentsOfFile_(icon_path())
                if ns_img:
                    NSApplication.sharedApplication().setApplicationIconImage_(ns_img)
            except Exception:
                pass

        self.hotkeys.start()
        self.tray.start()
        self._update_tray_title()
        if self._single_instance:
            self._single_instance.listen_for_activation(
                lambda: self.dispatch(self._on_activated_by_second_instance)
            )
        if not self.player.available:
            self.root.after(
                400,
                lambda: self.hud.show("VLC not found — install 64-bit VLC", self.config, 5000),
            )

    def _on_activated_by_second_instance(self) -> None:
        self.settings.open()
        self.hud.show("LoFi HUD is already running", self.config, 3000)

    def dispatch(self, action_or_fn: Any, *args: object) -> None:
        """Thread-safe and PyObjC-safe dispatch onto the Tk event loop via event notification."""
        self._action_queue.put((action_or_fn, args))
        try:
            self.root.event_generate("<<ActionQueue>>", when="tail")
        except Exception:
            try:
                self.root.after_idle(self._process_action_queue)
            except Exception:
                pass

    def _process_action_queue(self) -> None:
        try:
            while True:
                action_or_fn, args = self._action_queue.get_nowait()
                try:
                    if callable(action_or_fn):
                        action_or_fn(*args)
                    elif isinstance(action_or_fn, str):
                        self._run_action(action_or_fn, *args)
                except Exception as exc:
                    import traceback

                    traceback.print_exc()
        except queue.Empty:
            pass

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
            self._sync_monitors()

    def force_pause(self) -> None:
        if self.player.pause():
            self.toast("⏸ Paused", actions=True)
            self._update_tray_title()
            self._sync_monitors()

    def toggle_audio(self) -> None:
        if not self.player.available:
            self.toast("VLC not found — install 64-bit VLC", actions=True)
            return

        # If currently empty, auto-rescan the directory before giving up
        if not self.player.song_paths:
            self.player.load_library(self.config.music_dir)

        result = self.player.toggle()
        if result == "unavailable":
            self.toast("VLC not found — install 64-bit VLC", actions=True)
        elif result == "empty":
            self.toast("Folder Empty: Add MP3s", actions=True)
            self.open_music_folder()
        elif result == "pause":
            self.toast("⏸ Paused", actions=True)
            self._update_tray_title()
        elif result == "play":
            self.toast("▶ Resumed", actions=True)
            self._update_tray_title()
        self._sync_monitors()

    def rescan_library(self) -> None:
        if not self.player.available:
            self.toast("VLC not found — install 64-bit VLC", actions=True)
            return
        self.player.load_library(self.config.music_dir)
        count = len(self.player.song_paths)
        if count == 0:
            self.toast("Folder Empty: Add MP3s", actions=True)
        else:
            self.toast(f"Library Rescanned: {count} Tracks", actions=True)
        self._update_tray_title()
        self._sync_monitors()

    def next_track(self) -> None:
        self.player.next()
        self._update_tray_title()
        if self.player.is_playing:
            self._start_track_monitor(immediate=True)

    def prev_track(self) -> None:
        self.player.previous()
        self._update_tray_title()
        if self.player.is_playing:
            self._start_track_monitor(immediate=True)

    def open_music_folder(self) -> None:
        try:
            if not os.path.exists(self.config.music_dir):
                ensure_music_dir(self.config.music_dir)
            if hasattr(os, "startfile"):
                os.startfile(self.config.music_dir)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", self.config.music_dir])
            else:
                subprocess.Popen(["xdg-open", self.config.music_dir])
        except Exception:
            pass

    def _update_tray_title(self) -> None:
        song_name = self.player.clean_name()
        if self.player.is_playing:
            title = f"LoFi HUD ▶ {song_name}" if song_name else "LoFi HUD ▶ Playing"
        elif song_name:
            title = f"LoFi HUD ⏸ {song_name}"
        else:
            title = "LoFi HUD Idle"
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
        old_autopause = self.config.autopause_device
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
        self._sync_monitors()
        self.toast("Settings Saved!")

    def _sync_monitors(self) -> None:
        if self.player.is_playing:
            self._start_track_monitor(immediate=True)
            self._start_device_monitor()
        else:
            self._stop_track_monitor()
            self._stop_device_monitor()

    def _start_track_monitor(self, immediate: bool = False) -> None:
        self._stop_track_monitor()
        if immediate:
            self._track_monitor()
        else:
            self._track_monitor_timer = self.root.after(1500, self._track_monitor)

    def _stop_track_monitor(self) -> None:
        if self._track_monitor_timer is not None:
            try:
                self.root.after_cancel(self._track_monitor_timer)
            except Exception:
                pass
            self._track_monitor_timer = None

    def _start_device_monitor(self) -> None:
        self._stop_device_monitor()
        if self.config.autopause_device != "Disabled" and self.player.is_playing:
            self._device_monitor_timer = self.root.after(2000, self._device_monitor)

    def _stop_device_monitor(self) -> None:
        if self._device_monitor_timer is not None:
            try:
                self.root.after_cancel(self._device_monitor_timer)
            except Exception:
                pass
            self._device_monitor_timer = None

    def _track_monitor(self) -> None:
        self._track_monitor_timer = None
        if not self.player.is_playing:
            return

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

        if self.player.is_playing:
            self._track_monitor_timer = self.root.after(1500, self._track_monitor)

    def _device_monitor(self) -> None:
        self._device_monitor_timer = None
        target = self.config.autopause_device
        if target == "Disabled" or not self.player.is_playing:
            return

        active_names = get_active_audio_devices()
        if target in active_names:
            self._was_device_present = True
        elif self._was_device_present:
            self.force_pause()
            self.hud.show("⏸ Auto-Paused (Device Disconnected)", self.config, 5000)
            self._was_device_present = False
            return

        if self.player.is_playing and self.config.autopause_device != "Disabled":
            self._device_monitor_timer = self.root.after(2000, self._device_monitor)

    def _on_exit(self, *_args: object) -> None:
        self._stop_track_monitor()
        self._stop_device_monitor()
        if self._single_instance:
            self._single_instance.release()
        self.hotkeys.stop()
        self.player.stop()
        self.tray.stop()
        os._exit(0)

    def run(self) -> None:
        self.root.mainloop()
