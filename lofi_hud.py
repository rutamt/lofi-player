"""LoFi HUD entrypoint — DPI awareness and application bootstrap."""

from __future__ import annotations

import ctypes

from lofi.app import App
from lofi.instance import SingleInstance


def enable_dpi_awareness() -> None:
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass


def main() -> None:
    enable_dpi_awareness()

    single_instance = SingleInstance()
    if not single_instance.acquire():
        # Another instance is already running: signal it to surface its UI and cleanly exit
        single_instance.notify_running_instance()
        return

    App(single_instance=single_instance).run()


if __name__ == "__main__":
    main()
