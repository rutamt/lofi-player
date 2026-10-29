"""System tray icon and menu."""

from __future__ import annotations

import os
import sys
import threading
from typing import Callable, Optional

import PIL.Image
import PIL.ImageDraw
import pystray
from pystray import MenuItem as item

from lofi.paths import icon_path, tray_icon_path


def _create_default_menu_icon(size: int = 44) -> PIL.Image.Image:
    """Render a clean antialiased white music notes vector icon for macOS menu bar."""
    img = PIL.Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = PIL.ImageDraw.Draw(img)
    scale = size / 22.0
    center = size / 2.0
    fill = (255, 255, 255, 255)
    r = 2.4 * scale
    n1_x, n1_y = center - 4.5 * scale, center + 4.5 * scale
    n2_x, n2_y = center + 4.0 * scale, center + 2.0 * scale
    draw.ellipse([n1_x - r, n1_y - r * 0.8, n1_x + r, n1_y + r * 0.8], fill=fill)
    draw.ellipse([n2_x - r, n2_y - r * 0.8, n2_x + r, n2_y + r * 0.8], fill=fill)
    sw = 1.4 * scale
    top_y = center - 6.0 * scale
    draw.rectangle([n1_x + r - sw, top_y, n1_x + r, n1_y], fill=fill)
    draw.rectangle([n2_x + r - sw, top_y - 2.0 * scale, n2_x + r, n2_y], fill=fill)
    draw.polygon(
        [
            (n1_x + r - sw, top_y),
            (n2_x + r, top_y - 2.0 * scale),
            (n2_x + r, top_y),
            (n1_x + r - sw, top_y + 2.0 * scale),
        ],
        fill=fill,
    )
    return img


def load_icon() -> PIL.Image.Image:
    # 1. Custom user-provided tray icon (e.g. tray_icon.png in project root)
    tpath = tray_icon_path()
    if tpath and os.path.exists(tpath):
        try:
            return PIL.Image.open(tpath).convert("RGBA")
        except OSError:
            pass

    # 2. macOS native default: crisp white vector icon with transparent background
    if sys.platform == "darwin":
        return _create_default_menu_icon()

    # 3. Windows: use application icon or fallback colored circle
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
        if sys.platform == "darwin":
            self._icon.run_detached()
            try:
                if hasattr(self._icon, "_status_item") and self._icon._status_item:
                    btn = self._icon._status_item.button()
                    if btn and btn.image():
                        btn.image().setTemplate_(True)
            except Exception:
                pass
        else:
            self._thread = threading.Thread(target=self._icon.run, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        if self._icon is not None:
            try:
                self._icon.stop()
            except Exception:
                pass

