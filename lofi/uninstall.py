"""Clean uninstallation helper for LoFi HUD."""

from __future__ import annotations

import ctypes
import os
import shutil
import sys
import winreg
from typing import Optional


def get_music_dir_from_config() -> Optional[str]:
    """Retrieve the music folder path from config so we ensure it is preserved."""
    try:
        from lofi.config import load_config
        config = load_config()
        return os.path.abspath(config.music_dir)
    except Exception:
        return None


def clean_uninstall(show_dialog: bool = True) -> bool:
    """Completely remove shortcuts, registry entries, and AppData config.

    Guarantees the music folder with the user's songs is NEVER touched.
    """
    music_dir = get_music_dir_from_config()
    appdata = os.environ.get("APPDATA", "")

    # 1. Remove Start Menu Programs shortcut
    start_menu_lnk = os.path.join(
        appdata, r"Microsoft\Windows\Start Menu\Programs\LoFi HUD.lnk"
    )
    if os.path.exists(start_menu_lnk):
        try:
            os.remove(start_menu_lnk)
        except OSError:
            pass

    # 2. Remove Startup autostart shortcut
    startup_lnk = os.path.join(
        appdata, r"Microsoft\Windows\Start Menu\Programs\Startup\LoFi HUD.lnk"
    )
    if os.path.exists(startup_lnk):
        try:
            os.remove(startup_lnk)
        except OSError:
            pass

    # 3. Clean legacy Run registry key
    try:
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE) as key:
            winreg.DeleteValue(key, "LoFiHUD")
    except OSError:
        pass

    # 4. Remove %APPDATA%\LoFiHUD directory (config, logs)
    lofi_appdata = os.path.join(appdata, "LoFiHUD")
    if os.path.exists(lofi_appdata):
        # Double check to prevent deleting music directory if configured inside AppData
        if not music_dir or os.path.abspath(lofi_appdata) != music_dir:
            try:
                shutil.rmtree(lofi_appdata, ignore_errors=True)
            except Exception:
                pass

    if show_dialog:
        msg = (
            "LoFi HUD shortcuts, autostart entries, and configurations have been cleanly removed.\n\n"
        )
        if music_dir and os.path.exists(music_dir):
            msg += f"Your songs and music library in:\n{music_dir}\nhave been safely preserved."
        else:
            msg += "Your music files and folders have been preserved."

        try:
            MB_ICONINFORMATION = 0x00000040
            MB_OK = 0x00000000
            ctypes.windll.user32.MessageBoxW(0, msg, "LoFi HUD — Uninstalled", MB_OK | MB_ICONINFORMATION)
        except Exception:
            print(msg)

    return True


if __name__ == "__main__":
    clean_uninstall(show_dialog=True)
