"""Clean uninstallation helper for LoFi HUD."""

from __future__ import annotations

import os
import shutil
import sys
from typing import Optional

from lofi.paths import ignored_dir_for, user_data_dir


def get_music_dir_from_config() -> Optional[str]:
    """Retrieve the music folder path from config."""
    try:
        from lofi.config import load_config
        config = load_config()
        return os.path.abspath(config.music_dir)
    except Exception:
        return None


def clean_uninstall(
    show_dialog: bool = True,
    delete_music: Optional[bool] = None,
) -> bool:
    """Completely remove shortcuts, registry entries, and AppData / Application Support config.

    Optionally allows deleting the music library and songs if explicitly requested.
    Defaults to preserving music (No is the default selected option).
    """
    music_dir = get_music_dir_from_config()
    appdata = os.environ.get("APPDATA", "")

    # Prompt user whether to delete music if not specified
    if delete_music is None and show_dialog and music_dir and os.path.exists(music_dir):
        prompt = (
            f"Do you also want to permanently delete your music folder and all downloaded songs?\n\n"
            f"Folder: {music_dir}\n\n"
            f"• Click 'No' to KEEP your music (Recommended).\n"
            f"• Click 'Yes' to DELETE the music folder and all songs."
        )
        if sys.platform == "win32":
            import ctypes

            MB_YESNO = 0x00000004
            MB_DEFBUTTON2 = 0x00000100  # "No" is the default selected button
            MB_ICONQUESTION = 0x00000020
            IDYES = 6
            try:
                choice = ctypes.windll.user32.MessageBoxW(
                    0,
                    prompt,
                    "LoFi HUD — Remove Music Library?",
                    MB_YESNO | MB_DEFBUTTON2 | MB_ICONQUESTION,
                )
                delete_music = (choice == IDYES)
            except Exception:
                delete_music = False
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                delete_music = messagebox.askyesno(
                    "LoFi HUD — Remove Music Library?",
                    prompt,
                    default=messagebox.NO,
                )
                root.destroy()
            except Exception:
                delete_music = False
    elif delete_music is None:
        delete_music = False

    # Windows-specific shortcut and registry cleanup
    if sys.platform == "win32" and appdata:
        try:
            import winreg

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
        except Exception:
            pass

    # macOS LaunchAgent cleanup
    if sys.platform == "darwin":
        plist = os.path.expanduser("~/Library/LaunchAgents/com.rutamt.lofihud.plist")
        if os.path.exists(plist):
            try:
                os.remove(plist)
            except OSError:
                pass

    # 4. Remove user data / config directory
    config_dir = user_data_dir()
    if os.path.exists(config_dir):
        if not music_dir or os.path.abspath(config_dir) != music_dir:
            try:
                shutil.rmtree(config_dir, ignore_errors=True)
            except Exception:
                pass

    # 5. Handle music directory if user explicitly requested deletion
    if delete_music and music_dir and os.path.exists(music_dir):
        ignored = ignored_dir_for(music_dir)
        if os.path.exists(ignored):
            try:
                shutil.rmtree(ignored, ignore_errors=True)
            except Exception:
                pass

        norm_music = os.path.abspath(music_dir).lower().rstrip("\\/")
        user_profile = os.path.abspath(os.path.expanduser("~")).lower().rstrip("\\/")

        dangerous_paths = {
            user_profile,
            os.path.join(user_profile, "desktop"),
            os.path.join(user_profile, "documents"),
            os.path.join(user_profile, "downloads"),
            os.path.join(user_profile, "music"),
        }
        if sys.platform == "win32":
            system_drive = os.path.abspath(os.environ.get("SystemDrive", "C:") + "\\").lower().rstrip("\\/")
            dangerous_paths.add(system_drive)

        if norm_music in dangerous_paths:
            from lofi.engine import VALID_EXTENSIONS
            for root_d, _subdirs, files in os.walk(music_dir):
                for f in files:
                    if f.lower().endswith(VALID_EXTENSIONS):
                        try:
                            os.remove(os.path.join(root_d, f))
                        except OSError:
                            pass
        else:
            try:
                shutil.rmtree(music_dir, ignore_errors=True)
            except Exception:
                pass

    # 6. Show final confirmation dialog
    if show_dialog:
        if delete_music:
            msg = (
                "LoFi HUD has been successfully uninstalled.\n\n"
                "Shortcuts, settings, and your music library have been completely removed."
            )
        elif music_dir and os.path.exists(music_dir):
            msg = (
                "LoFi HUD shortcuts, autostart entries, and configurations have been cleanly removed.\n\n"
                f"Your songs and music library in:\n{music_dir}\n"
                "have been safely preserved."
            )
        else:
            msg = (
                "LoFi HUD shortcuts, autostart entries, and configurations have been cleanly removed.\n\n"
                "Your music files and folders have been preserved."
            )

        if sys.platform == "win32":
            import ctypes
            try:
                MB_ICONINFORMATION = 0x00000040
                MB_OK = 0x00000000
                ctypes.windll.user32.MessageBoxW(0, msg, "LoFi HUD — Uninstalled", MB_OK | MB_ICONINFORMATION)
            except Exception:
                print(msg)
        else:
            try:
                import tkinter as tk
                from tkinter import messagebox
                root = tk.Tk()
                root.withdraw()
                messagebox.showinfo("LoFi HUD — Uninstalled", msg)
                root.destroy()
            except Exception:
                print(msg)

    return True


if __name__ == "__main__":
    clean_uninstall(show_dialog=True)
