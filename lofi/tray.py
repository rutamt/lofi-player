"""System tray icon and menu."""

from __future__ import annotations

import os
import threading
from typing import Callable, Optional

import PIL.Image
import PIL.ImageDraw
import pystray
from pystray import MenuItem as item

from lofi.paths import icon_path


def load_icon() -> PIL.Image.Image:
    path = icon_path()
    if os.path.exists(path):
        try:
            return PIL.Image.open(path)
        except OSError:
            pass
    image = PIL.Image.new("RGB", (64, 64), color=(255, 255, 255))
    draw = PIL.ImageDraw.Draw(image)
    draw.ellipse((10, 10, 54, 54), fill=(0, 229, 255))
    return image


class Tray:
    def __init__(
        self,
        on_settings: Callable[[], None],
        on_toggle: Callable[[], None],
        on_next: Callable[[], None],
        on_rescan: Callable[[], None],
        on_open_folder: Callable[[], None],
        on_exit: Callable[[], None],
    ) -> None:
        self._icon: Optional[pystray.Icon] = None
        self._thread: Optional[threading.Thread] = None
        self._on_exit = on_exit

        menu = pystray.Menu(
            item("Settings (Double-Click)", lambda _i, _j: on_settings(), default=True),
            item("Play/Pause", lambda _i, _j: on_toggle()),
            item("Next Track", lambda _i, _j: on_next()),
            item("Rescan Library", lambda _i, _j: on_rescan()),
            item("Open Music Folder", lambda _i, _j: on_open_folder()),
            item("Exit", lambda _i, _j: on_exit()),
        )
        self._icon = pystray.Icon("LoFi HUD", load_icon(), "LoFi HUD Idle", menu)

    def set_title(self, title: str) -> None:
        if self._icon is not None:
            try:
                # Windows notify icon tooltip is capped at 128 characters
                self._icon.title = title[:120]
            except Exception:
                pass

    def start(self) -> None:
        assert self._icon is not None
        self._thread = threading.Thread(target=self._icon.run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

