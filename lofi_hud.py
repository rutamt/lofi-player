"""LoFi HUD entrypoint — DPI awareness and application bootstrap."""

from __future__ import annotations

import ctypes

from lofi.app import App


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
    App().run()


if __name__ == "__main__":
    main()
