"""Frozen vs source path resolution for config, icons, and music."""

from __future__ import annotations

import os
import sys


def application_dir() -> str:
    """Directory that holds `config.json` and the default Lofi folder."""
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def bundle_dir() -> str:
    """Directory that contains bundled assets such as `icon.ico`."""
    if getattr(sys, "frozen", False):
        return getattr(sys, "_MEIPASS", application_dir())
    return application_dir()


def user_data_dir() -> str:
    """Directory for persisting configuration in standard Windows AppData."""
    appdata = os.environ.get("APPDATA")
    if appdata:
        path = os.path.join(appdata, "LoFiHUD")
        try:
            os.makedirs(path, exist_ok=True)
            return path
        except OSError:
            pass
    return application_dir()


def config_path() -> str:
    # If a config.json already exists next to the executable (portable / dev mode), use it
    local = os.path.join(application_dir(), "config.json")
    if os.path.exists(local):
        return local
    return os.path.join(user_data_dir(), "config.json")


def default_music_dir() -> str:
    # If local Lofi folder exists (portable / repository mode), use it
    local_lofi = os.path.join(application_dir(), "Lofi")
    if os.path.exists(local_lofi):
        return local_lofi
    # Otherwise default to standard user Music\LoFi directory
    user_music = os.path.join(os.path.expanduser("~"), "Music", "LoFi")
    return user_music


def icon_path() -> str:
    return os.path.join(bundle_dir(), "icon.ico")


def ignored_dir_for(music_dir: str) -> str:
    """Sibling `Ignored_Lofi` folder next to the configured music directory."""
    parent = os.path.dirname(os.path.normpath(music_dir))
    return os.path.join(parent, "Ignored_Lofi")
