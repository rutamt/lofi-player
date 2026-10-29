"""Modern DPI-aware floating toast HUD overlay with Windows 11 styling."""

from __future__ import annotations

import re
import sys
import tkinter as tk
from typing import Dict, Optional, Tuple

import customtkinter as ctk
from PIL import Image, ImageDraw

from lofi.config import AppConfig
from lofi.themes import Theme, get_theme

# Win32 Constants
if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    GWL_EXSTYLE = -20
    WS_EX_NOACTIVATE = 0x08000000
    DWMWA_WINDOW_CORNER_PREFERENCE = 33
    DWMWCP_ROUND = 2

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]


def _get_primary_monitor_work_area() -> Tuple[int, int, int, int]:
    """Return (left, top, width, height) of the primary display's work area."""
    if sys.platform == "win32":
        try:
            user32 = ctypes.windll.user32
            rc = RECT()
            # SPI_GETWORKAREA = 0x0030 retrieves the work area of the primary display
            if user32.SystemParametersInfoW(0x0030, 0, ctypes.byref(rc), 0):
                return rc.left, rc.top, rc.right - rc.left, rc.bottom - rc.top
        except Exception:
            pass

        try:
            user32 = ctypes.windll.user32
            return 0, 0, user32.GetSystemMetrics(0), user32.GetSystemMetrics(1)
        except Exception:
            pass

    # macOS or fallback
    try:
        root = tk._default_root
        if root:
            sw = root.winfo_screenwidth()
            sh = root.winfo_screenheight()
            top_offset = 28 if sys.platform == "darwin" else 0
            return 0, top_offset, sw, sh - top_offset
    except Exception:
        pass

    return 0, 0, 1920, 1080


def _create_vector_icon(icon_type: str, color: str, size: int = 22) -> ctk.CTkImage:
    """Render a crisp, antialiased vector icon with pixel-perfect centering."""
    scale = 3
    S = size * scale
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    c = color.lstrip("#")
    rgb = tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))
    fill = rgb + (255,)
    center = S / 2.0

    if icon_type == "play":
        hw = 5.0 * scale
        hh = 7.0 * scale
        pts = [
            (center - hw * 0.7 + 1.2 * scale, center - hh),
            (center - hw * 0.7 + 1.2 * scale, center + hh),
            (center + hw * 1.2 + 1.2 * scale, center),
        ]
        draw.polygon(pts, fill=fill)
    elif icon_type == "pause":
        bw = 3.5 * scale
        bh = 13.0 * scale
        gap = 3.5 * scale
        x1 = center - gap / 2.0 - bw
        x2 = center + gap / 2.0
        y1 = center - bh / 2.0
        y2 = center + bh / 2.0
        draw.rounded_rectangle([x1, y1, x1 + bw, y2], radius=1.5 * scale, fill=fill)
        draw.rounded_rectangle([x2, y1, x2 + bw, y2], radius=1.5 * scale, fill=fill)
    elif icon_type == "volume":
        bx1 = center - 6.0 * scale
        bx2 = center - 2.5 * scale
        by1 = center - 3.0 * scale
        by2 = center + 3.0 * scale
        draw.rectangle([bx1, by1, bx2, by2], fill=fill)
        cone = [
            (bx2, by1),
            (center + 1.5 * scale, center - 6.5 * scale),
            (center + 1.5 * scale, center + 6.5 * scale),
            (bx2, by2),
        ]
        draw.polygon(cone, fill=fill)
        draw.arc(
            [center - 2.5 * scale, center - 4.5 * scale, center + 4.5 * scale, center + 4.5 * scale],
            start=300,
            end=60,
            fill=fill,
            width=int(1.5 * scale),
        )
        draw.arc(
            [center - 5.0 * scale, center - 7.5 * scale, center + 7.5 * scale, center + 7.5 * scale],
            start=310,
            end=50,
            fill=fill,
            width=int(1.5 * scale),
        )
    elif icon_type == "trash":
        w = 10.0 * scale
        h = 12.0 * scale
        x1, x2 = center - w / 2, center + w / 2
        y1, y2 = center - h / 2 + 1.5 * scale, center + h / 2
        draw.rectangle([x1 - 1.5 * scale, y1 - 2.5 * scale, x2 + 1.5 * scale, y1 - 1.0 * scale], fill=fill)
        draw.rectangle([center - 2.0 * scale, y1 - 4.0 * scale, center + 2.0 * scale, y1 - 2.5 * scale], fill=fill)
        draw.rounded_rectangle([x1, y1, x2, y2], radius=1.5 * scale, fill=fill)
    elif icon_type in ("settings", "check"):
        pts = [
            (center - 6.0 * scale, center),
            (center - 1.5 * scale, center + 4.5 * scale),
            (center + 6.0 * scale, center - 4.5 * scale),
        ]
        draw.line(pts, fill=fill, width=int(2.0 * scale), joint="curve")
    elif icon_type == "error":
        r = 5.0 * scale
        draw.line([(center - r, center - r), (center + r, center + r)], fill=fill, width=int(2.0 * scale))
        draw.line([(center - r, center + r), (center + r, center - r)], fill=fill, width=int(2.0 * scale))
    else:  # music
        r = 2.5 * scale
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

    resized = img.resize((size, size), Image.Resampling.LANCZOS)
    return ctk.CTkImage(light_image=resized, dark_image=resized, size=(size, size))


def _parse_message(
    message: str,
    badge: Optional[str] = None,
    title: Optional[str] = None,
    icon: Optional[str] = None,
    progress: Optional[int] = None,
) -> Tuple[str, str, str, Optional[int]]:
    """Parse message string into (icon_name, badge, title, progress)."""
    if badge is not None and title is not None and icon is not None:
        return icon, badge, title, progress

    # Volume change: "🔊 Volume: 45%"
    vol_match = re.search(r"Volume:\s*(\d+)%", message, re.IGNORECASE)
    if vol_match:
        val = int(vol_match.group(1))
        return "volume", "VOLUME", f"{val}%", val

    # Now playing with prefix: "🎵 Now Playing: Song Name"
    np_match = re.match(r"^🎵\s*Now Playing:\s*(.+)$", message)
    if np_match:
        return "music", "NOW PLAYING", np_match.group(1).strip(), None

    # Track info: "🎵 Song Name"
    song_match = re.match(r"^🎵\s*(.+)$", message)
    if song_match:
        return "music", "NOW PLAYING", song_match.group(1).strip(), None

    # Playback states
    if "▶" in message or "Resumed" in message:
        return "play", "PLAYBACK", "Resumed", None
    if "Auto-Paused" in message:
        return "pause", "AUTO-PAUSED", "Device Disconnected", None
    if "⏸" in message or "Paused" in message:
        return "pause", "PLAYBACK", "Paused", None

    # Removed song
    rem_match = re.match(r"^🗑\s*Removed:\s*(.+)$", message)
    if rem_match:
        return "trash", "REMOVED", rem_match.group(1).strip(), None

    # Error
    if "❌" in message or "Failed" in message:
        clean = message.replace("❌", "").strip()
        return "error", "ERROR", clean, None

    if "Folder Empty" in message:
        return "music", "LIBRARY", "Folder Empty: Add MP3s", None

    if "Library Rescanned" in message:
        return "check", "LIBRARY", message, None

    if "already running" in message.lower():
        return "check", "ACTIVE", "Already Running in Background", None

    if "Settings Saved" in message:
        return "check", "SETTINGS", "Settings Saved!", None

    if "VLC" in message:
        return "error", "ERROR", message, None

    return icon or "music", badge or "LOFI HUD", title or message, progress


def _hex_to_nscolor(hex_str: str, alpha: float = 1.0) -> Any:
    """Convert hex color string to AppKit.NSColor."""
    try:
        import AppKit
        s = hex_str.lstrip("#")
        if len(s) == 6:
            r = int(s[0:2], 16) / 255.0
            g = int(s[2:4], 16) / 255.0
            b = int(s[4:6], 16) / 255.0
            return AppKit.NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, alpha)
        return AppKit.NSColor.whiteColor()
    except Exception:
        return None


DARWIN_SYMBOL_MAP = {
    "play": "play.fill",
    "pause": "pause.fill",
    "volume": "speaker.wave.2.fill",
    "trash": "trash.fill",
    "settings": "checkmark",
    "check": "checkmark",
    "error": "xmark",
    "music": "music.note",
}

try:
    import warnings
    import objc
    warnings.filterwarnings("ignore", category=objc.ObjCPointerWarning)
except Exception:
    pass


class _DarwinGlassHud:
    """Hardware-accelerated native macOS liquid glass HUD overlay using AppKit."""

    def __init__(self, root: tk.Misc) -> None:
        import AppKit

        self._root = root
        self._hide_timer: Optional[str] = None
        self._theme: Optional[Theme] = None

        self._panel = AppKit.NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            AppKit.NSMakeRect(100, 100, 320, 68),
            AppKit.NSWindowStyleMaskBorderless,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        self._panel.setOpaque_(False)
        self._panel.setBackgroundColor_(AppKit.NSColor.clearColor())
        self._panel.setLevel_(AppKit.NSStatusWindowLevel)
        self._panel.setHasShadow_(True)
        self._panel.setHidesOnDeactivate_(False)
        self._panel.setIgnoresMouseEvents_(True)
        self._panel.setAlphaValue_(0.0)

        cv = self._panel.contentView()
        self._ve = AppKit.NSVisualEffectView.alloc().initWithFrame_(cv.bounds())
        self._ve.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
        self._ve.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
        self._ve.setState_(AppKit.NSVisualEffectStateActive)
        self._ve.setWantsLayer_(True)
        self._ve.layer().setCornerRadius_(20.0)
        self._ve.layer().setMasksToBounds_(True)
        self._ve.layer().setBorderWidth_(1.0)
        self._ve.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.22).CGColor())
        self._ve.setAutoresizingMask_(18)
        cv.addSubview_(self._ve)

        # Icon tile container
        self._tile = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(14, 14, 40, 40))
        self._tile.setWantsLayer_(True)
        self._tile.layer().setCornerRadius_(11.0)
        self._tile.layer().setMasksToBounds_(True)
        self._tile.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.10).CGColor())
        self._tile.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.20).CGColor())
        self._tile.layer().setBorderWidth_(1.0)
        self._ve.addSubview_(self._tile)

        # Icon image view
        self._icon_view = AppKit.NSImageView.alloc().initWithFrame_(AppKit.NSMakeRect(9, 9, 22, 22))
        self._tile.addSubview_(self._icon_view)

        # Header badge label
        self._badge = AppKit.NSTextField.labelWithString_("NOW PLAYING")
        self._badge.setFrame_(AppKit.NSMakeRect(66, 38, 160, 16))
        self._badge.setFont_(AppKit.NSFont.boldSystemFontOfSize_(10.0))
        self._ve.addSubview_(self._badge)

        # Volume percent label (right aligned)
        self._percent = AppKit.NSTextField.labelWithString_("")
        self._percent.setFont_(AppKit.NSFont.boldSystemFontOfSize_(10.0))
        self._percent.setAlignment_(AppKit.NSTextAlignmentRight)
        self._ve.addSubview_(self._percent)

        # Main Title label
        self._title = AppKit.NSTextField.labelWithString_("")
        self._title.setFrame_(AppKit.NSMakeRect(66, 14, 230, 22))
        self._title.setFont_(AppKit.NSFont.systemFontOfSize_weight_(14.0, AppKit.NSFontWeightSemibold))
        self._title.setLineBreakMode_(AppKit.NSLineBreakByTruncatingTail)
        self._ve.addSubview_(self._title)

        # Progress bar track & fill for volume
        self._prog_track = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(66, 20, 210, 6))
        self._prog_track.setWantsLayer_(True)
        self._prog_track.layer().setCornerRadius_(3.0)
        self._prog_track.layer().setMasksToBounds_(True)
        self._prog_track.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.15).CGColor())

        self._prog_fill = AppKit.NSView.alloc().initWithFrame_(AppKit.NSMakeRect(0, 0, 0, 6))
        self._prog_fill.setWantsLayer_(True)
        self._prog_fill.layer().setCornerRadius_(3.0)
        self._prog_track.addSubview_(self._prog_fill)
        self._ve.addSubview_(self._prog_track)

    def apply_theme(self, theme: Theme) -> None:
        import AppKit

        self._theme = theme
        is_light = getattr(theme, "appearance", "dark") == "light"

        accent_ns = _hex_to_nscolor(theme.accent)
        muted_ns = _hex_to_nscolor(theme.muted)
        fg_ns = _hex_to_nscolor(theme.fg)

        if is_light:
            self._ve.setMaterial_(AppKit.NSVisualEffectMaterialPopover)
            self._ve.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(0.0, 0.12).CGColor())
            self._tile.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(0.0, 0.05).CGColor())
            self._tile.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(0.0, 0.10).CGColor())
            self._prog_track.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(0.0, 0.12).CGColor())
        else:
            self._ve.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
            self._ve.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.22).CGColor())
            self._tile.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.10).CGColor())
            self._tile.layer().setBorderColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.20).CGColor())
            self._prog_track.layer().setBackgroundColor_(AppKit.NSColor.colorWithWhite_alpha_(1.0, 0.15).CGColor())

        self._badge.setTextColor_(accent_ns)
        self._percent.setTextColor_(muted_ns)
        self._title.setTextColor_(fg_ns)
        self._icon_view.setContentTintColor_(accent_ns)
        self._prog_fill.layer().setBackgroundColor_(accent_ns.CGColor())

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
        import AppKit

        theme = get_theme(config.theme)
        self.apply_theme(theme)

        icon_val, badge_val, title_val, prog_val = _parse_message(
            message, badge=badge, title=title, icon=icon, progress=progress
        )

        sym_name = DARWIN_SYMBOL_MAP.get(icon_val, "music.note")
        sym = AppKit.NSImage.imageWithSystemSymbolName_accessibilityDescription_(sym_name, None)
        if sym:
            cfg = AppKit.NSImageSymbolConfiguration.configurationWithPointSize_weight_(16.0, AppKit.NSFontWeightBold)
            sym = sym.imageWithSymbolConfiguration_(cfg)
            self._icon_view.setImage_(sym)

        self._badge.setStringValue_(badge_val)

        hud_h = 68
        if prog_val is not None:
            hud_w = 300
            self._title.setHidden_(True)
            self._prog_track.setHidden_(False)
            self._percent.setHidden_(False)
            self._percent.setStringValue_(f"{prog_val}%")
            self._percent.setFrame_(AppKit.NSMakeRect(hud_w - 75, 38, 55, 16))

            track_w = hud_w - 86
            self._prog_track.setFrame_(AppKit.NSMakeRect(66, 20, track_w, 6))
            fill_w = max(0, min(track_w, int(track_w * (prog_val / 100.0))))
            self._prog_fill.setFrame_(AppKit.NSMakeRect(0, 0, fill_w, 6))
        else:
            self._percent.setHidden_(True)
            self._prog_track.setHidden_(True)
            self._title.setHidden_(False)
            display_title = title_val
            if len(display_title) > 42:
                display_title = display_title[:39] + "..."
            self._title.setStringValue_(display_title)

            font = self._title.font()
            str_size = AppKit.NSString.stringWithString_(display_title).sizeWithAttributes_({
                AppKit.NSFontAttributeName: font
            })
            calc_w = int(str_size.width) + 90
            hud_w = max(240, min(420, calc_w))
            self._title.setFrame_(AppKit.NSMakeRect(66, 14, hud_w - 80, 22))

        screen = AppKit.NSScreen.mainScreen()
        vf = screen.visibleFrame() if screen else AppKit.NSMakeRect(0, 0, 1440, 900)
        pad_x, pad_y = 30, 40
        pos = config.hud_position

        if pos == "Top Left":
            x = vf.origin.x + pad_x
            y = vf.origin.y + vf.size.height - hud_h - pad_y
        elif pos == "Top Center":
            x = vf.origin.x + (vf.size.width - hud_w) / 2
            y = vf.origin.y + vf.size.height - hud_h - pad_y
        elif pos == "Top Right":
            x = vf.origin.x + vf.size.width - hud_w - pad_x
            y = vf.origin.y + vf.size.height - hud_h - pad_y
        elif pos == "Bottom Left":
            x = vf.origin.x + pad_x
            y = vf.origin.y + pad_y
        elif pos == "Bottom Right":
            x = vf.origin.x + vf.size.width - hud_w - pad_x
            y = vf.origin.y + pad_y
        elif pos == "Center":
            x = vf.origin.x + (vf.size.width - hud_w) / 2
            y = vf.origin.y + (vf.size.height - hud_h) / 2
        else:  # Bottom Center
            x = vf.origin.x + (vf.size.width - hud_w) / 2
            y = vf.origin.y + pad_y

        self._panel.setFrame_display_(AppKit.NSMakeRect(x, y, hud_w, hud_h), True)
        self._panel.invalidateShadow()

        if self._hide_timer is not None:
            self._root.after_cancel(self._hide_timer)
            self._hide_timer = None

        self._panel.setAlphaValue_(0.96)
        self._panel.orderFrontRegardless()

        timeout = duration_override if duration_override is not None else config.hud_timeout
        self._hide_timer = self._root.after(timeout, self.hide)

    def hide(self) -> None:
        import AppKit

        if self._hide_timer is not None:
            self._root.after_cancel(self._hide_timer)
            self._hide_timer = None

        try:
            AppKit.NSAnimationContext.beginGrouping()
            AppKit.NSAnimationContext.currentContext().setDuration_(0.18)
            self._panel.animator().setAlphaValue_(0.0)
            AppKit.NSAnimationContext.endGrouping()
            self._root.after(200, lambda: self._panel.orderOut_(None))
        except Exception:
            self._panel.orderOut_(None)


class Hud:
    """Modern floating toast overlay anchored to main display with clean vector icons."""

    def __new__(cls, root: tk.Misc) -> Any:
        if sys.platform == "darwin":
            try:
                return _DarwinGlassHud(root)
            except Exception:
                pass
        return super().__new__(cls)

    def __init__(self, root: tk.Misc) -> None:
        self._root = root
        self._hide_timer: Optional[str] = None
        self._fade_timer: Optional[str] = None
        self._is_darwin = sys.platform == "darwin"
        self._target_alpha = 0.96 if self._is_darwin else 0.98
        self._is_visible = False
        self._icon_cache: Dict[Tuple[str, str], ctk.CTkImage] = {}
        self._ns_window = None
        self._ve_view = None

        self._window = ctk.CTkToplevel(root)
        self._window.overrideredirect(True)
        self._window.attributes("-topmost", True)
        self._window.attributes("-alpha", 0.0)
        self._window.withdraw()

        if self._is_darwin:
            self._apply_darwin_styles()
        else:
            self._apply_win32_styles()

        # Outer card container - smooth modern capsule corner radius on macOS
        card_radius = 20 if self._is_darwin else 14
        self._container = ctk.CTkFrame(
            self._window,
            corner_radius=card_radius,
            border_width=1,
        )
        self._container.pack(fill="both", expand=True)

        # Left: Icon avatar box
        icon_radius = 12 if self._is_darwin else 10
        self._icon_box = ctk.CTkFrame(
            self._container,
            width=40,
            height=40,
            corner_radius=icon_radius,
            border_width=1,
        )
        self._icon_box.pack(side="left", padx=(12, 10), pady=10)
        self._icon_box.pack_propagate(False)

        self._icon_label = ctk.CTkLabel(
            self._icon_box,
            text="",
        )
        self._icon_label.place(relx=0.5, rely=0.5, anchor="center")

        # Right: Content - vertically centered
        self._content = ctk.CTkFrame(self._container, fg_color="transparent")
        self._content.pack(side="left", fill="x", expand=True, padx=(0, 14))

        # Header: badge + optional percentage
        self._header = ctk.CTkFrame(self._content, fg_color="transparent")
        self._header.pack(fill="x", anchor="w")

        self._badge_label = ctk.CTkLabel(
            self._header,
            text="NOW PLAYING",
            font=("Segoe UI", 9, "bold"),
            anchor="w",
            height=0,
        )
        self._badge_label.pack(side="left")

        self._percent_label = ctk.CTkLabel(
            self._header,
            text="",
            font=("Segoe UI", 9, "bold"),
            anchor="e",
            height=0,
        )

        # Main: Title
        self._title_label = ctk.CTkLabel(
            self._content,
            text="",
            font=("Segoe UI", 14, "bold"),
            anchor="w",
            height=0,
        )
        self._title_label.pack(fill="x", pady=(2, 0))

        # Progress bar for volume
        self._progress_bar = ctk.CTkProgressBar(
            self._content,
            height=6,
            corner_radius=3,
            border_width=0,
        )

    def _apply_darwin_styles(self) -> None:
        """Configure hardware-accelerated liquid glass blur and shadow on macOS."""
        try:
            import AppKit

            self._window.title("__LOFI_HUD_OVERLAY__")
            self._window.attributes("-transparent", 1)
            self._window.configure(fg_color="systemTransparent")
            self._window.config(bg="systemTransparent")

            # Realize the native Cocoa window so AppKit can locate and configure it
            self._window.deiconify()
            self._window.update_idletasks()

            app = AppKit.NSApplication.sharedApplication()
            for win in app.windows():
                if win.title() == "__LOFI_HUD_OVERLAY__":
                    win.setOpaque_(False)
                    win.setBackgroundColor_(AppKit.NSColor.clearColor())
                    win.setHasShadow_(True)

                    cv = win.contentView()
                    tf = cv.superview() if cv is not None else None
                    ve = None
                    if tf is not None:
                        for sv in tf.subviews():
                            if isinstance(sv, AppKit.NSVisualEffectView):
                                ve = sv
                                break
                    if ve is None and cv is not None:
                        ve = AppKit.NSVisualEffectView.alloc().initWithFrame_(cv.bounds())
                        ve.setAutoresizingMask_(18)
                        cv.addSubview_positioned_relativeTo_(ve, AppKit.NSWindowBelow, None)

                    if ve is not None:
                        ve.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)
                        ve.setBlendingMode_(AppKit.NSVisualEffectBlendingModeBehindWindow)
                        ve.setState_(AppKit.NSVisualEffectStateActive)
                        ve.setWantsLayer_(True)
                        ve.layer().setCornerRadius_(20.0)
                        ve.layer().setMasksToBounds_(True)

                    win.invalidateShadow()
                    self._ns_window = win
                    self._ve_view = ve
                    break

            self._window.withdraw()
        except Exception:
            pass

    def _apply_win32_styles(self) -> None:
        """Configure non-activating style and Windows 11 rounded corners."""
        if sys.platform != "win32":
            return
        try:
            hwnd = ctypes.windll.user32.GetParent(self._window.winfo_id()) or self._window.winfo_id()

            # Prevent stealing focus from active window
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
        self._theme = theme

        if self._is_darwin and self._ve_view is not None:
            try:
                import AppKit

                # Adaptive blur material for light vs dark appearance
                if getattr(theme, "appearance", "dark") == "light":
                    self._ve_view.setMaterial_(AppKit.NSVisualEffectMaterialPopover)
                else:
                    self._ve_view.setMaterial_(AppKit.NSVisualEffectMaterialHUDWindow)

                rim_color = _glass_rim_color(theme.border, getattr(theme, "appearance", "dark"))
                self._window.configure(fg_color="systemTransparent")
                self._window.config(bg="systemTransparent")
                self._container.configure(
                    fg_color="transparent",
                    border_color=rim_color,
                )
                self._icon_box.configure(
                    fg_color="transparent",
                    border_color=rim_color,
                )
            except Exception:
                self._window.configure(fg_color=theme.surface)
                self._container.configure(
                    fg_color=theme.surface,
                    border_color=theme.border,
                )
                self._icon_box.configure(
                    fg_color=theme.bg,
                    border_color=theme.border,
                )
        else:
            self._window.configure(fg_color=theme.surface)
            self._container.configure(
                fg_color=theme.surface,
                border_color=theme.border,
            )
            self._icon_box.configure(
                fg_color=theme.bg,
                border_color=theme.border,
            )

        self._badge_label.configure(text_color=theme.accent)
        self._percent_label.configure(text_color=theme.muted)
        self._title_label.configure(text_color=theme.fg)
        self._progress_bar.configure(
            fg_color=theme.surface_alt,
            progress_color=theme.accent,
        )

    def _get_icon(self, icon_name: str, color: str) -> ctk.CTkImage:
        key = (icon_name, color)
        if key not in self._icon_cache:
            self._icon_cache[key] = _create_vector_icon(icon_name, color, size=22)
        return self._icon_cache[key]

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

        icon_img = self._get_icon(icon_val, theme.accent)
        self._icon_label.configure(image=icon_img)
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

        # Anchored strictly to the primary (main) display
        mon_x, mon_y, mon_w, mon_h = _get_primary_monitor_work_area()

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
        if self._ns_window is not None:
            try:
                self._ns_window.invalidateShadow()
            except Exception:
                pass

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
        try:
            if not self._window.winfo_exists():
                self._fade_timer = None
                return
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
        except Exception:
            self._fade_timer = None
