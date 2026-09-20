"""Modern DPI-aware floating toast HUD overlay with Windows 11 styling."""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import re
import tkinter as tk
from typing import Optional, Tuple

import customtkinter as ctk

from lofi.config import AppConfig
from lofi.themes import Theme, get_theme

# Win32 Constants
GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
DWMWA_WINDOW_CORNER_PREFERENCE = 33
DWMWCP_ROUND = 2
MONITOR_DEFAULTTONEAREST = 2


class RECT(ctypes.Structure):
    _fields_ = [
        ("left", wintypes.LONG),
        ("top", wintypes.LONG),
        ("right", wintypes.LONG),
        ("bottom", wintypes.LONG),
    ]


class MONITORINFO(ctypes.Structure):
    _fields_ = [
        ("cbSize", wintypes.DWORD),
        ("rcMonitor", RECT),
        ("rcWork", RECT),
        ("dwFlags", wintypes.DWORD),
    ]


def _get_active_monitor_work_area() -> Tuple[int, int, int, int]:
    """Return (left, top, width, height) of the active monitor's work area."""
    try:
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        if hwnd:
            hmon = user32.MonitorFromWindow(hwnd, MONITOR_DEFAULTTONEAREST)
            if hmon:
                mi = MONITORINFO()
                mi.cbSize = ctypes.sizeof(MONITORINFO)
                if user32.GetMonitorInfoW(hmon, ctypes.byref(mi)):
                    rc = mi.rcWork
                    return rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top
    except Exception:
        pass

    try:
        user32 = ctypes.windll.user32
        return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
    except Exception:
        return 0, 0, 1920, 1080


def _parse_message(
    message: str,
    badge: Optional[str] = None,
    title: Optional[str] = None,
    icon: Optional[str] = None,
    progress: Optional[int] = None,
) -> Tuple[str, str, str, Optional[int]]:
    """Parse message string into (icon, badge, title, progress)."""
    if badge is not None and title is not None and icon is not None:
        return icon, badge, title, progress

    # Volume change: "🔊 Volume: 45%"
    vol_match = re.search(r"Volume:\s*(\d+)%", message, re.IGNORECASE)
    if vol_match:
        val = int(vol_match.group(1))
        return "🔊", "VOLUME", f"{val}%", val

    # Now playing with prefix: "🎵 Now Playing: Song Name"
    np_match = re.match(r"^🎵\s*Now Playing:\s*(.+)$", message)
    if np_match:
        return "🎵", "NOW PLAYING", np_match.group(1).strip(), None

    # Track info: "🎵 Song Name"
    song_match = re.match(r"^🎵\s*(.+)$", message)
    if song_match:
        return "🎵", "NOW PLAYING", song_match.group(1).strip(), None

    # Playback states
    if "▶" in message or "Resumed" in message:
        return "▶", "PLAYBACK", "Resumed", None
    if "Auto-Paused" in message:
        return "⏸", "AUTO-PAUSED", "Device Disconnected", None
    if "⏸" in message or "Paused" in message:
        return "⏸", "PLAYBACK", "Paused", None

    # Removed song
    rem_match = re.match(r"^🗑\s*Removed:\s*(.+)$", message)
    if rem_match:
        return "🗑", "REMOVED", rem_match.group(1).strip(), None

    # Error
    if "❌" in message or "Failed" in message:
        clean = message.replace("❌", "").strip()
        return "❌", "ERROR", clean, None

    if "Folder Empty" in message:
        return "📁", "LIBRARY", "Folder Empty: Add MP3s", None

    if "Settings Saved" in message:
        return "⚙", "SETTINGS", "Settings Saved!", None

    if "VLC" in message:
        return "⚠️", "ERROR", message, None

    return icon or "🎵", badge or "LOFI HUD", title or message, progress


class Hud:
    """Modern floating toast overlay with clean rounded pill design and no-flicker updates."""

    def __init__(self, root: tk.Misc) -> None:
        self._root = root
        self._hide_timer: Optional[str] = None
        self._fade_timer: Optional[str] = None
        self._target_alpha = 0.98
        self._is_visible = False

        self._window = ctk.CTkToplevel(root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", 0.0)
        self._window.withdraw()

        self._apply_win32_styles()

        # Outer card container - fills window completely with 1px border
        self._container = ctk.CTkFrame(
            self._window,
            corner_radius=14,
            border_width=1,
        )
        self._container.pack(fill="both", expand=True)

        # Left: Icon avatar box
        self._icon_box = ctk.CTkFrame(
            self._container,
            width=40,
            height=40,
            corner_radius=10,
            border_width=1,
        )
        self._icon_box.pack(side="left", padx=(12, 10), pady=10)
        self._icon_box.pack_propagate(False)

        self._icon_label = ctk.CTkLabel(
            self._icon_box,
            text="🎵",
            font=("Segoe UI", 20),
        )
        self._icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Right: Content
        self._content = ctk.CTkFrame(self._container, fg_color="transparent")
        self._content.pack(side="left", fill="both", expand=True, padx=(0, 14), pady=8)

        # Header: badge + optional percentage
        self._header = ctk.CTkFrame(self._content, fg_color="transparent")
        self._header.pack(fill="x", anchor="w")

        self._badge_label = ctk.CTkLabel(
            self._header,
            text="NOW PLAYING",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
        )
        self._badge_label.pack(side="left")

        self._percent_label = ctk.CTkLabel(
            self._header,
            text="",
            font=("Segoe UI", 9, "bold"),
            anchor="e",
        )

        # Main: Title
        self._title_label = ctk.CTkLabel(
            self._content,
            text="",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
        )
        self._title_label.pack(fill="x", pady=(1, 0))

        # Progress bar for volume
        self._progress_bar = ctk.CTkProgressBar(
            self._content,
            height=6,
            corner_radius=3,
            border_width=0,
        )

    def _apply_win32_styles(self) -> None:
        """Configure non-activating style and Windows 11 rounded corners."""
        try:
            hwnd = ctypes.windll.user32.GetParent(self._window.winfo_id()) or self._window.winfo_id()

            # Prevent stealing focus from the active window
            ex_style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style | WS_EX_NOACTIVATE)

            # Windows 11 rounded corners
            corner_val = ctypes.c_int(DWMWCP_ROUND)
            ctypes.windll.dwmapi.DwmSetWindowAttribute(
                hwnd, DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(corner_val), ctypes.sizeof(corner_val)
            )
        except Exception:
            pass

    def apply_theme(self, theme: Theme) -> None:
        """Apply theme color tokens across the HUD components."""
        self._window.configure(fg_color=theme.surface)
        self._container.configure(
            fg_color=theme.surface,
            border_color=theme.border,
        )
        self._icon_box.configure(
            fg_color=theme.bg,
            border_color=theme.border,
        )
        self._icon_label.configure(text_color=theme.accent)
        self._badge_label.configure(text_color=theme.accent)
        self._percent_label.configure(text_color=theme.muted)
        self._title_label.configure(text_color=theme.fg)
        self._progress_bar.configure(
            fg_color=theme.surface_alt,
            progress_color=theme.accent,
        )

    def show(
        self,
        message: str,
        config: AppConfig,
        duration_override: Optional[int] = None,
        *,
        badge: Optional[str] = None,
        title: Optional[str] = None,
        icon: Optional[str] = None,
        progress: Optional[int] = None,
    ) -> None:
        """Display toast with structured content, dynamic sizing, and no flicker."""
        theme = get_theme(config.theme)
        self.apply_theme(theme)

        icon_val, badge_val, title_val, prog_val = _parse_message(
            message, badge=badge, title=title, icon=icon, progress=progress
        )

        self._icon_label.configure(text=icon_val)
        self._badge_label.configure(text=badge_val)

        if prog_val is not None:
            # Volume mode
            self._title_label.pack_forget()
            self._percent_label.configure(text=f"{prog_val}%")
            self._percent_label.pack(side="right")
            self._progress_bar.set(max(0.0, min(1.0, prog_val / 100.0)))
            self._progress_bar.pack(fill="x", pady=(4, 0))
            hud_w = 300
        else:
            # Info / track mode
            self._percent_label.pack_forget()
            self._progress_bar.pack_forget()
            display_title = title_val
            if len(display_title) > 38:
                display_title = display_title[:35] + "..."
            self._title_label.configure(text=display_title)
            self._title_label.pack(fill="x", pady=(1, 0))

            # Dynamic width: compact for short actions, wider for track titles
            self._window.update_idletasks()
            req_w = self._window.winfo_reqwidth()
            hud_w = max(200, min(420, req_w + 20))

        self._window.deiconify()
        self._window.update_idletasks()
        hud_h = max(68, self._window.winfo_reqheight())

        mon_x, mon_y, mon_w, mon_h = _get_active_monitor_work_area()

        pad_x, pad_y = 30, 40
        pos = config.hud_position
        if pos == "Top Left":
            x = mon_x + pad_x
            y = mon_y + pad_y
        elif pos == "Top Center":
            x = mon_x + (mon_w - hud_w) // 2
            y = mon_y + pad_y
        elif pos == "Top Right":
            x = mon_x + mon_w - hud_w - pad_x
            y = mon_y + pad_y
        elif pos == "Bottom Left":
            x = mon_x + pad_x
            y = mon_y + mon_h - hud_h - pad_y
        elif pos == "Bottom Right":
            x = mon_x + mon_w - hud_w - pad_x
            y = mon_y + mon_h - hud_h - pad_y
        elif pos == "Center":
            x = mon_x + (mon_w - hud_w) // 2
            y = mon_y + (mon_h - hud_h) // 2
        else:  # Bottom Center
            x = mon_x + (mon_w - hud_w) // 2
            y = mon_y + mon_h - hud_h - pad_y

        self._window.geometry(f"{hud_w}x{hud_h}+{x}+{y}")

        # Cancel any pending timers
        if self._fade_timer is not None:
            self._root.after_cancel(self._fade_timer)
            self._fade_timer = None
        if self._hide_timer is not None:
            self._root.after_cancel(self._hide_timer)
            self._hide_timer = None

        # Avoid flashing: directly set alpha
        self._window.attributes("-alpha", self._target_alpha)
        self._is_visible = True

        timeout = duration_override if duration_override is not None else config.hud_timeout
        self._hide_timer = self._root.after(timeout, self.hide)

    def hide(self) -> None:
        """Fade out and hide the HUD overlay."""
        if self._hide_timer is not None:
            self._root.after_cancel(self._hide_timer)
            self._hide_timer = None
        if self._fade_timer is not None:
            self._root.after_cancel(self._fade_timer)
            self._fade_timer = None
        self._fade_out(4)

    def _fade_out(self, step: int) -> None:
        total_steps = 4
        if step >= 0:
            alpha = self._target_alpha * (step / float(total_steps))
            self._window.attributes("-alpha", alpha)
            self._fade_timer = self._root.after(25, self._fade_out, step - 1)
        else:
            self._fade_timer = None
            self._is_visible = False
            self._window.attributes("-alpha", 0.0)
            self._window.withdraw()
