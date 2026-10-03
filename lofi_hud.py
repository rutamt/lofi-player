"""LoFi HUD entrypoint — DPI awareness and application bootstrap."""

from __future__ import annotations

import ctypes

import sys

from lofi.app import App
from lofi.instance import SingleInstance
from lofi.uninstall import clean_uninstall


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    if "--uninstall" in sys.argv or "/uninstall" in sys.argv:
        delete_music = None
        if "--delete-music" in sys.argv:
            delete_music = True
        elif "--keep-music" in sys.argv or "--preserve-music" in sys.argv:
            delete_music = False
        clean_uninstall(show_dialog=True, delete_music=delete_music)
        return

    enable_dpi_awareness()

    single_instance = SingleInstance()
    if not single_instance.acquire():
        # Another instance is already running: signal it to surface its UI and cleanly exit
        single_instance.notify_running_instance()
        return

    App(single_instance=single_instance).run()


if __name__ == "__main__":
    main()
