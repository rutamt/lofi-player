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


def config_path() -> str:
    return os.path.join(application_dir(), "config.json")


def default_music_dir() -> str:
    return os.path.join(application_dir(), "Lofi")


def icon_path() -> str:
    return os.path.join(bundle_dir(), "icon.ico")


def ignored_dir_for(music_dir: str) -> str:
    """Sibling `Ignored_Lofi` folder next to the configured music directory."""
    parent = os.path.dirname(os.path.normpath(music_dir))
    return os.path.join(parent, "Ignored_Lofi")
