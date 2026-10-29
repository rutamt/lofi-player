"""Tabbed CustomTkinter settings window."""

from __future__ import annotations

import os
import sys
from dataclasses import replace
from typing import Callable, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog

from lofi.config import AppConfig
from lofi.paths import icon_path
from lofi.themes import Theme, get_theme, is_system_dark, theme_id_for_label, theme_labels

TIMEOUT_MAP = {
    1000: "1 Second",
    1500: "1.5 Seconds",
    2000: "2 Seconds",
    3500: "3.5 Seconds",
    5000: "5 Seconds",
}
REVERSE_TIMEOUT = {label: ms for ms, label in TIMEOUT_MAP.items()}
HUD_POSITIONS = [
    "Top Left",
    "Top Center",
    "Top Right",
    "Bottom Left",
    "Bottom Center",
    "Bottom Right",
    "Center",
]
BIND_ROWS = (
    ("Play/Pause", "key_play"),
    ("Next Track", "key_next"),
    ("Previous Track", "key_prev"),
    ("Show Song Name", "key_show_song"),
    ("Remove/Ignore Song", "key_ignore"),
    ("Volume Up", "key_vol_up"),
    ("Volume Down", "key_vol_down"),
)

LABEL_WIDTH = 190
CONTROL_WIDTH = 240
CARD_RADIUS = 12
PAD = 16


class SettingsController:
    """Owns the singleton settings Toplevel and remembers window position."""

    def __init__(
        self,
        root: ctk.CTk,
        get_config: Callable[[], AppConfig],
        save_config: Callable[[AppConfig], None],
        get_devices: Callable[[], List[str]],
        set_binding: Callable[[bool], None],
        on_rescan: Optional[Callable[[], None]] = None,
    ) -> None:
        self._root = root
        self._get_config = get_config
        self._save_config = save_config
        self._get_devices = get_devices
        self._set_binding = set_binding
        self._on_rescan = on_rescan
        self._window: Optional[ctk.CTkToplevel] = None
        self._last_geometry: Optional[str] = None

    def open(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.deiconify()
            self._window.lift()
            self._window.focus_force()
            if sys.platform == "darwin":
                self._activate_macos()
            return
        self._window = SettingsWindow(
            self._root,
            self._get_config(),
            self._save_config,
            self._get_devices,
            self._set_binding,
            on_close=self._on_close,
            initial_geometry=self._last_geometry,
            on_rescan=self._on_rescan,
        )
        self._window.deiconify()
        self._window.lift()
        self._window.focus_force()
        if sys.platform == "darwin":
            self._activate_macos()
            self._window.after(50, self._window.lift)
            self._window.after(100, self._window.focus_force)

    def _activate_macos(self) -> None:
        try:
            from Cocoa import NSApplication, NSApplicationActivationPolicyRegular

            app = NSApplication.sharedApplication()
            app.setActivationPolicy_(NSApplicationActivationPolicyRegular)
            app.activateIgnoringOtherApps_(True)
        except Exception:
            pass

    def _on_close(self, geometry: Optional[str] = None) -> None:
        if geometry:
            self._last_geometry = geometry
        self._window = None


class SettingsWindow(ctk.CTkToplevel):
    def __init__(
        self,
        root: ctk.CTk,
        config: AppConfig,
        on_save: Callable[[AppConfig], None],
        get_devices: Callable[[], List[str]],
        set_binding: Callable[[bool], None],
        on_close: Callable[[Optional[str]], None],
        initial_geometry: Optional[str] = None,
        on_rescan: Optional[Callable[[], None]] = None,
    ) -> None:
        super().__init__(root)
        self._config = config
        self._on_save = on_save
        self._set_binding = set_binding
        self._on_close = on_close
        self._on_rescan = on_rescan
        self._theme = get_theme(config.theme)
        self._capturing = False
        self._cancel_capture: Optional[Callable[[], None]] = None
        self._binds: Dict[str, str] = {
            "key_play": config.key_play,
            "key_next": config.key_next,
            "key_prev": config.key_prev,
            "key_show_song": config.key_show_song,
            "key_ignore": config.key_ignore,
            "key_vol_up": config.key_vol_up,
            "key_vol_down": config.key_vol_down,
        }

        # Themeable element registry for live updating
        self._cards: List[ctk.CTkFrame] = []
        self._plain_frames: List[tuple[tk.Frame, str]] = []
        self._labels: List[ctk.CTkLabel] = []
        self._menus: List[ctk.CTkOptionMenu] = []
        self._switches: List[ctk.CTkSwitch] = []
        self._buttons: List[ctk.CTkButton] = []
        self._secondary_buttons: List[ctk.CTkButton] = []
        self._entries: List[ctk.CTkEntry] = []

        self.title("LoFi HUD Settings")
        if initial_geometry:
            self.geometry(initial_geometry)
        else:
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            w = 640
            h = min(780, max(680, sh - 80))
            x = max(0, (sw - w) // 2)
            y = max(0, (sh - h) // 2)
            self.geometry(f"{w}x{h}+{x}+{y}")
        self.minsize(580, 520)
        self.protocol("WM_DELETE_WINDOW", self._destroy)

        icon = icon_path()
        if os.path.exists(icon):
            self.after(200, lambda: self._try_icon(icon))

        theme = self._theme
        self.configure(fg_color=theme.bg)
        try:
            ctk.set_appearance_mode(theme.appearance)
        except Exception:
            pass

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self._header = tk.Frame(self, bg=theme.bg)
        self._header.grid(row=0, column=0, sticky="ew", padx=20, pady=(16, 12))
        self._header_title = ctk.CTkLabel(
            self._header,
            text="LoFi HUD",
            font=("Segoe UI", 24, "bold"),
            text_color=theme.fg,
        )
        self._header_title.pack(anchor="w")
        self._header_sub = ctk.CTkLabel(
            self._header,
            text="Playback, overlay, and hotkeys",
            font=("Segoe UI", 13),
            text_color=theme.muted,
        )
        self._header_sub.pack(anchor="w", pady=(2, 0))

        self._tabs = ctk.CTkTabview(
            self,
            corner_radius=CARD_RADIUS,
            fg_color=theme.surface,
            segmented_button_fg_color=theme.surface_alt,
            segmented_button_selected_color=theme.accent,
            segmented_button_selected_hover_color=theme.accent_hover,
            segmented_button_unselected_color=theme.surface_alt,
            segmented_button_unselected_hover_color=theme.border,
            text_color="#fafafa",
            text_color_disabled=theme.muted,
        )
        self._tabs.grid(row=1, column=0, sticky="nsew", padx=20)
        try:
            self._tabs._canvas.tk.call("lower", self._tabs._canvas._w)
        except Exception:
            pass
        self._tabs.add("Appearance")
        self._tabs.add("Playback")
        self._tabs.add("Controls")

        self._scroll_frames: List[ctk.CTkScrollableFrame] = []

        self._tab_app_scroll = ctk.CTkScrollableFrame(
            self._tabs.tab("Appearance"),
            fg_color="transparent",
            scrollbar_button_color=theme.accent,
            scrollbar_button_hover_color=theme.accent_hover,
        )
        self._tab_app_scroll.pack(fill="both", expand=True)
        self._scroll_frames.append(self._tab_app_scroll)
        self._build_appearance(self._tab_app_scroll)

        self._tab_play_scroll = ctk.CTkScrollableFrame(
            self._tabs.tab("Playback"),
            fg_color="transparent",
            scrollbar_button_color=theme.accent,
            scrollbar_button_hover_color=theme.accent_hover,
        )
        self._tab_play_scroll.pack(fill="both", expand=True)
        self._scroll_frames.append(self._tab_play_scroll)
        self._build_playback(self._tab_play_scroll, get_devices())

        self._tab_ctrl_scroll = ctk.CTkScrollableFrame(
            self._tabs.tab("Controls"),
            fg_color="transparent",
            scrollbar_button_color=theme.accent,
            scrollbar_button_hover_color=theme.accent_hover,
        )
        self._tab_ctrl_scroll.pack(fill="both", expand=True)
        self._scroll_frames.append(self._tab_ctrl_scroll)
        self._build_controls(self._tab_ctrl_scroll)

        for sf, tname in (
            (self._tab_app_scroll, "Appearance"),
            (self._tab_play_scroll, "Playback"),
            (self._tab_ctrl_scroll, "Controls"),
        ):
            sf._check_if_valid_scroll = self._make_valid_scroll_check(tname)

        self.bind("<MouseWheel>", self._on_window_mouse_wheel, add=True)
        try:
            self._tabs._canvas.bind("<MouseWheel>", self._on_window_mouse_wheel, add=True)
        except Exception:
            pass
        if sys.platform not in ("darwin", "win32"):
            self.bind("<Button-4>", self._on_window_mouse_wheel, add=True)
            self.bind("<Button-5>", self._on_window_mouse_wheel, add=True)

        self._footer = tk.Frame(self, bg=theme.bg)
        self._footer.grid(row=2, column=0, sticky="ew", padx=20, pady=(16, 16))
        self._save_btn = ctk.CTkButton(
            self._footer,
            text="Save & Apply",
            command=self._save,
            font=("Segoe UI", 14, "bold"),
            height=42,
            corner_radius=10,
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
        )
        from lofi import __version__

        self._save_btn.pack(fill="x")

        self._footer_info = tk.Frame(self._footer, bg=theme.bg)
        self._footer_info.pack(pady=(8, 0))

        self._footer_lbl = ctk.CTkLabel(
            self._footer_info,
            text=f"LoFi HUD v{__version__} • Created by Rutam and Gemini",
            font=("Segoe UI", 11),
            text_color=theme.muted,
        )
        self._footer_lbl.pack(side="left")

        sep = ctk.CTkLabel(
            self._footer_info,
            text="  •  ",
            font=("Segoe UI", 11),
            text_color=theme.muted,
        )
        sep.pack(side="left")
        self._labels.append(sep)

        self._uninstall_btn = ctk.CTkButton(
            self._footer_info,
            text="Uninstall",
            font=("Segoe UI", 11, "underline"),
            text_color=theme.muted,
            fg_color="transparent",
            hover_color=theme.surface_alt,
            corner_radius=4,
            width=0,
            height=20,
            cursor="hand2" if sys.platform != "darwin" else "pointinghand",
            command=self._uninstall_action,
        )
        self._uninstall_btn.pack(side="left")
        self._uninstall_btn.bind(
            "<Enter>", lambda e: self._uninstall_btn.configure(text_color="#ef4444")
        )
        self._uninstall_btn.bind(
            "<Leave>", lambda e: self._uninstall_btn.configure(text_color=self._theme.muted)
        )

        self.update_idletasks()
        self.deiconify()
        self.lift()
        self.focus_force()

        self._last_sys_dark = is_system_dark()
        self.after(1500, self._check_system_theme_change)

    def _check_system_theme_change(self) -> None:
        try:
            current_choice = theme_id_for_label(self._theme_var.get())
            if current_choice == "system":
                cur_dark = is_system_dark()
                if getattr(self, "_last_sys_dark", None) is not None and cur_dark != self._last_sys_dark:
                    self._last_sys_dark = cur_dark
                    new_theme = get_theme("system")
                    self.apply_theme(new_theme)
                self._last_sys_dark = cur_dark
        except Exception:
            pass
        try:
            self.after(1500, self._check_system_theme_change)
        except Exception:
            pass

    def _make_valid_scroll_check(self, tab_name: str) -> Callable[[object], bool]:
        def _check(widget: object) -> bool:
            try:
                if self._tabs.get() != tab_name:
                    return False
                if not widget:
                    return True
                top = getattr(widget, "winfo_toplevel", None)
                if top and top() == self:
                    return True
            except Exception:
                pass
            return False

        return _check

    def _on_window_mouse_wheel(self, event: tk.Event) -> None:
        try:
            tab_name = self._tabs.get()
            scroll_map = {
                "Appearance": self._tab_app_scroll,
                "Playback": self._tab_play_scroll,
                "Controls": self._tab_ctrl_scroll,
            }
            active_sf = scroll_map.get(tab_name)
            if not active_sf:
                return

            canvas = getattr(active_sf, "_parent_canvas", None)
            if not canvas:
                return

            delta = getattr(event, "delta", 0)
            num = getattr(event, "num", None)

            if sys.platform == "darwin":
                if delta != 0:
                    step = -int(delta / 30) if abs(delta) >= 120 else -int(delta * 2)
                    if step != 0:
                        canvas.yview("scroll", step, "units")
            elif sys.platform.startswith("win"):
                if delta != 0:
                    step = -int(delta / 40) if abs(delta) >= 120 else -int(delta)
                    canvas.yview("scroll", step, "units")
            else:
                if num == 4:
                    canvas.yview("scroll", -2, "units")
                elif num == 5:
                    canvas.yview("scroll", 2, "units")
        except Exception:
            pass

    def apply_theme(self, theme: Theme) -> None:
        """Dynamically re-color all widgets in-place without closing or flickering."""
        self._theme = theme
        try:
            ctk.set_appearance_mode(theme.appearance)
        except Exception:
            pass
        self.configure(fg_color=theme.bg)
        self._header_title.configure(text_color=theme.fg)
        self._header_sub.configure(text_color=theme.muted)

        self._tabs.configure(
            fg_color=theme.surface,
            segmented_button_fg_color=theme.surface_alt,
            segmented_button_selected_color=theme.accent,
            segmented_button_selected_hover_color=theme.accent_hover,
            segmented_button_unselected_color=theme.surface_alt,
            segmented_button_unselected_hover_color=theme.border,
            text_color="#ffffff" if theme.appearance == "dark" else "#1c1c1e",
        )

        for sf in getattr(self, "_scroll_frames", []):
            try:
                sf.configure(
                    scrollbar_button_color=theme.accent,
                    scrollbar_button_hover_color=theme.accent_hover,
                )
            except Exception:
                pass

        for card in self._cards:
            card.configure(fg_color=theme.surface_alt)

        for lbl in self._labels:
            lbl.configure(text_color=theme.fg)

        for menu in self._menus:
            menu.configure(
                fg_color=theme.accent,
                button_color=theme.accent,
                button_hover_color=theme.accent_hover,
                text_color=theme.accent_on_accent,
                dropdown_fg_color=theme.surface,
                dropdown_hover_color=theme.surface_alt,
                dropdown_text_color=theme.fg,
            )

        for switch in self._switches:
            switch.configure(
                progress_color=theme.accent,
                button_color=theme.fg,
                text_color=theme.fg,
            )

        for btn in self._buttons:
            btn.configure(
                fg_color=theme.accent,
                hover_color=theme.accent_hover,
                text_color=theme.accent_on_accent,
            )

        for s_btn in self._secondary_buttons:
            s_btn.configure(
                fg_color=theme.surface,
                border_color=theme.border,
                text_color=theme.fg,
            )

        for entry in self._entries:
            entry.configure(
                fg_color=theme.surface,
                border_color=theme.border,
                text_color=theme.fg,
            )

        for frame, prop in self._plain_frames:
            try:
                frame.configure(bg=getattr(theme, prop))
            except Exception:
                pass

        for f in (self._header, self._footer, self._footer_info):
            try:
                f.configure(bg=theme.bg)
            except Exception:
                pass

        self._save_btn.configure(
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
        )
        self._footer_lbl.configure(text_color=theme.muted)
        if hasattr(self, "_uninstall_btn"):
            self._uninstall_btn.configure(
                text_color=theme.muted,
                hover_color=theme.surface_alt,
            )

    def _try_icon(self, path: str) -> None:
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage

                ns_img = NSImage.alloc().initWithContentsOfFile_(path)
                if ns_img:
                    NSApplication.sharedApplication().setApplicationIconImage_(ns_img)
            except Exception:
                pass
        try:
            from PIL import Image, ImageTk

            self._icon_photo = ImageTk.PhotoImage(Image.open(path))
            self.iconphoto(False, self._icon_photo)
        except Exception:
            pass
        try:
            self.iconbitmap(path)
        except Exception:
            pass


    def _card(self, parent: tk.Misc, title: str) -> ctk.CTkFrame:
        theme = self._theme
        card = ctk.CTkFrame(
            parent,
            corner_radius=CARD_RADIUS,
            fg_color=theme.surface_alt,
        )
        card.pack(fill="x", padx=8, pady=(8, 4))
        try:
            card._canvas.tk.call("lower", card._canvas._w)
        except Exception:
            pass
        title_lbl = ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=theme.fg,
        )
        title_lbl.pack(anchor="w", padx=PAD, pady=(PAD, 6))
        self._cards.append(card)
        self._labels.append(title_lbl)
        return card

    def _row(self, parent: tk.Misc, label: str) -> tk.Frame:
        row = tk.Frame(parent, bg=self._theme.surface_alt)
        row.pack(fill="x", padx=PAD, pady=6)
        row.grid_columnconfigure(1, weight=1)
        row_lbl = ctk.CTkLabel(
            row,
            text=label,
            width=LABEL_WIDTH,
            anchor="w",
            font=("Segoe UI", 12),
            text_color=self._theme.fg,
        )
        row_lbl.grid(row=0, column=0, sticky="w")
        self._labels.append(row_lbl)
        self._plain_frames.append((row, "surface_alt"))
        return row

    def _menu(
        self,
        parent: tk.Misc,
        variable: ctk.StringVar,
        values: List[str],
        width: int = CONTROL_WIDTH,
        command: Optional[Callable[[str], None]] = None,
    ) -> ctk.CTkOptionMenu:
        theme = self._theme
        menu = ctk.CTkOptionMenu(
            parent,
            variable=variable,
            values=values,
            width=width,
            fg_color=theme.accent,
            button_color=theme.accent,
            button_hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
            dropdown_fg_color=theme.surface,
            dropdown_hover_color=theme.surface_alt,
            dropdown_text_color=theme.fg,
            command=command,
        )
        menu.grid(row=0, column=1, sticky="e")
        self._menus.append(menu)
        return menu

    def _switch(self, parent: tk.Misc, text: str, variable: ctk.BooleanVar, pady: tuple[int, int] = (0, 8)) -> ctk.CTkSwitch:
        theme = self._theme
        switch = ctk.CTkSwitch(
            parent,
            text=text,
            variable=variable,
            progress_color=theme.accent,
            button_color=theme.fg,
            font=("Segoe UI", 12),
            text_color=theme.fg,
        )
        switch.pack(anchor="w", padx=PAD, pady=pady)
        self._switches.append(switch)
        return switch

    def _on_theme_select(self, label: str) -> None:
        new_theme = get_theme(theme_id_for_label(label))
        self.apply_theme(new_theme)

    def _build_appearance(self, parent: tk.Misc) -> None:
        config = self._config
        theme = get_theme(config.theme)
        card = self._card(parent, "Theme & overlay")

        row = self._row(card, "Active Theme")
        current_theme_id = getattr(config, "theme", "system")
        current_label = "System (Auto)" if current_theme_id in ("system", "auto", "") else theme.label
        self._theme_var = ctk.StringVar(value=current_label)
        self._menu(row, self._theme_var, theme_labels(), command=self._on_theme_select)

        row = self._row(card, "HUD Position")
        self._pos_var = ctk.StringVar(value=config.hud_position)
        self._menu(row, self._pos_var, HUD_POSITIONS)

        row = self._row(card, "Action HUD Timeout")
        self._time_var = ctk.StringVar(
            value=TIMEOUT_MAP.get(config.hud_timeout, "2 Seconds")
        )
        self._menu(row, self._time_var, list(TIMEOUT_MAP.values()))

        row = self._row(card, "Song Info Timeout")
        self._song_time_var = ctk.StringVar(
            value=TIMEOUT_MAP.get(config.hud_song_timeout, "3.5 Seconds")
        )
        self._menu(row, self._song_time_var, list(TIMEOUT_MAP.values()))
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    def _build_playback(self, parent: tk.Misc, devices: List[str]) -> None:
        config = self._config
        card = self._card(parent, "Behavior & System")

        self._now_playing_var = ctk.BooleanVar(value=config.show_now_playing)
        self._actions_var = ctk.BooleanVar(value=config.show_actions)
        self._autostart_var = ctk.BooleanVar(value=getattr(config, "autostart", True))

        autostart_label = "Start LoFi HUD at login" if sys.platform == "darwin" else "Start LoFi HUD with Windows"
        self._switch(card, autostart_label, self._autostart_var, pady=(4, 8))
        self._switch(card, "Auto-show Now Playing when the track changes", self._now_playing_var)
        self._switch(card, "Show volume and play/pause HUD", self._actions_var)

        opts = ["Disabled"] + devices
        if config.autopause_device not in opts:
            opts.append(config.autopause_device)
        row = self._row(card, "Auto-Pause Device")
        self._device_var = ctk.StringVar(value=config.autopause_device)
        self._menu(row, self._device_var, opts)
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

        source = self._card(parent, "Music source")
        dir_frame = tk.Frame(source, bg=self._theme.surface_alt)
        dir_frame.pack(fill="x", padx=PAD, pady=(4, 8))
        self._plain_frames.append((dir_frame, "surface_alt"))
        theme = self._theme
        self._dir_entry = ctk.CTkEntry(
            dir_frame,
            fg_color=theme.surface,
            border_color=theme.border,
            text_color=theme.fg,
        )
        self._dir_entry.insert(0, config.music_dir)
        self._dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        self._entries.append(self._dir_entry)

        browse_btn = ctk.CTkButton(
            dir_frame,
            text="Browse",
            width=88,
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
            command=self._browse,
        )
        browse_btn.pack(side="right")
        self._buttons.append(browse_btn)

        action_frame = tk.Frame(source, bg=self._theme.surface_alt)
        action_frame.pack(fill="x", padx=PAD, pady=(0, PAD))
        self._plain_frames.append((action_frame, "surface_alt"))

        open_btn = ctk.CTkButton(
            action_frame,
            text="Open Folder",
            width=110,
            fg_color=theme.surface,
            hover_color=theme.border,
            text_color=theme.fg,
            command=self._open_folder_action,
        )
        open_btn.pack(side="left", padx=(0, 8))
        self._secondary_buttons.append(open_btn)

        if self._on_rescan:
            rescan_btn = ctk.CTkButton(
                action_frame,
                text="Rescan Library",
                width=120,
                fg_color=theme.surface,
                hover_color=theme.border,
                text_color=theme.fg,
                command=self._on_rescan,
            )
            rescan_btn.pack(side="left")
            self._secondary_buttons.append(rescan_btn)
        ctk.CTkFrame(source, height=12, fg_color="transparent").pack()

    def _open_folder_action(self) -> None:
        path = self._dir_entry.get().strip()
        if not path:
            return
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            if hasattr(os, "startfile"):
                os.startfile(path)
            elif sys.platform == "darwin":
                import subprocess

                subprocess.Popen(["open", path])
            else:
                import subprocess

                subprocess.Popen(["xdg-open", path])
        except Exception:
            pass

    def _uninstall_action(self) -> None:
        from lofi.paths import application_dir
        from lofi.uninstall import clean_uninstall
        import subprocess

        unins_exe = os.path.join(application_dir(), "unins000.exe")
        if os.path.exists(unins_exe):
            self._destroy()
            try:
                subprocess.Popen([unins_exe, "/SILENT"])
            except Exception:
                pass
            return

        import tkinter.messagebox as mb
        choice = mb.askyesno(
            "Uninstall LoFi HUD",
            "Are you sure you want to remove LoFi HUD, its shortcuts, and all application configurations from your system?\n\n(Your music folder and songs will be preserved).",
            parent=self,
        )
        if choice:
            self._destroy()
            clean_uninstall(show_dialog=True, delete_music=False)

    def _build_controls(self, parent: tk.Misc) -> None:
        config = self._config
        if sys.platform == "darwin":
            try:
                from lofi.input import is_accessibility_trusted, open_accessibility_settings

                access_card = self._card(parent, "macOS Permissions")
                trusted = is_accessibility_trusted(prompt=False)
                exec_path = os.path.abspath(sys.executable)
                is_translocated = "/Volumes/" in exec_path or "AppTranslocation" in exec_path

                if is_translocated:
                    status_text = "⚠ App Running from Disk Image"
                    status_color = "#f39c12"
                    desc_text = "Drag 'LoFi HUD.app' into /Applications and launch it from there. macOS blocks permanent accessibility permissions when running directly from a disk image."
                elif trusted:
                    status_text = "✓ Accessibility Granted"
                    status_color = "#2ecc71"
                    desc_text = "Global hotkeys are active and authorized by macOS."
                else:
                    status_text = "⚠ Accessibility Permission Needed"
                    status_color = "#f39c12"
                    desc_text = (
                        "Global hotkeys require Accessibility access in macOS System Settings.\n\n"
                        "Tip: If already checked in Settings, macOS may be caching an old build's hash. "
                        "Select 'LoFi HUD' in Accessibility and click the minus (-) button to remove it, "
                        "or run 'tccutil reset Accessibility com.rutamt.lofihud' in Terminal."
                    )

                access_lbl = ctk.CTkLabel(
                    access_card,
                    text=status_text,
                    font=("Segoe UI", 13, "bold"),
                    text_color=status_color,
                )
                access_lbl.pack(anchor="w", padx=PAD, pady=(4, 4))

                desc_lbl = ctk.CTkLabel(
                    access_card,
                    text=desc_text,
                    font=("Segoe UI", 11),
                    text_color=self._theme.muted,
                    wraplength=520,
                    justify="left",
                )
                desc_lbl.pack(anchor="w", padx=PAD, pady=(0, 8))
                self._labels.append(desc_lbl)

                btn_row = tk.Frame(access_card, bg=self._theme.surface_alt)
                btn_row.pack(fill="x", padx=PAD, pady=(0, PAD))
                self._plain_frames.append((btn_row, "surface_alt"))

                open_sec_btn = ctk.CTkButton(
                    btn_row,
                    text="Open Accessibility Settings",
                    command=open_accessibility_settings,
                    font=("Segoe UI", 12),
                    height=30,
                    fg_color=self._theme.accent,
                    hover_color=self._theme.accent_hover,
                    text_color=self._theme.accent_on_accent,
                )
                open_sec_btn.pack(side="left", padx=(0, 8))
                self._buttons.append(open_sec_btn)

                prompt_btn = ctk.CTkButton(
                    btn_row,
                    text="Request OS Prompt",
                    command=lambda: is_accessibility_trusted(prompt=True),
                    font=("Segoe UI", 12),
                    height=30,
                    fg_color=self._theme.surface,
                    hover_color=self._theme.border,
                    text_color=self._theme.fg,
                )
                prompt_btn.pack(side="left")
                self._secondary_buttons.append(prompt_btn)
            except Exception:
                pass

        card = self._card(parent, "Keybinds")

        self._hardware_var = ctk.BooleanVar(value=config.enable_hardware_keys)
        self._switch(card, "Enable hardware media keys", self._hardware_var, pady=(4, 8))

        row = self._row(card, "Hold Modifier")
        current_mod = config.mod_key.upper()
        if sys.platform == "darwin" and current_mod == "ALT":
            current_mod = "OPTION"
        self._mod_var = ctk.StringVar(value=current_mod)
        mod_options = ["CMD", "OPTION", "CTRL", "SHIFT"] if sys.platform == "darwin" else ["ALT", "CTRL", "SHIFT"]
        self._menu(row, self._mod_var, mod_options, width=160)

        for label, key_name in BIND_ROWS:
            self._add_bind_row(card, label, key_name)
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

    def _add_bind_row(self, parent: tk.Misc, label: str, config_key: str) -> None:
        theme = self._theme
        row = self._row(parent, label)
        button = ctk.CTkButton(
            row,
            text=self._binds[config_key].upper(),
            width=160,
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
        )
        button.grid(row=0, column=1, sticky="e")
        button.configure(command=lambda k=config_key, b=button: self._start_capture(k, b))
        self._buttons.append(button)

    def _start_capture(self, config_key: str, button: ctk.CTkButton) -> None:
        if self._cancel_capture is not None:
            self._cancel_capture()

        self._capturing = True
        theme = self._theme
        self._set_binding(True)
        button.configure(
            text="Press key...",
            fg_color=theme.danger,
            hover_color=theme.danger_hover,
            text_color="#ffffff",
        )

        SPECIAL_KEYSYM_MAP = {
            "space": "space",
            "up": "up",
            "down": "down",
            "left": "left",
            "right": "right",
            "return": "enter",
            "enter": "enter",
            "tab": "tab",
            "backspace": "backspace",
            "delete": "delete",
            "minus": "-",
            "equal": "=",
            "bracketleft": "[",
            "bracketright": "]",
            "semicolon": ";",
            "apostrophe": "'",
            "comma": ",",
            "period": ".",
            "slash": "/",
            "backslash": "\\",
            "grave": "`",
        }

        MODIFIER_KEYSYMS = {
            "alt_l", "alt_r", "option", "meta_l", "meta_r",
            "control_l", "control_r", "ctrl",
            "shift_l", "shift_r",
            "super_l", "super_r", "command",
            "iso_level3_shift", "mode_switch",
            "caps_lock", "num_lock",
        }

        def cleanup(new_key: Optional[str] = None) -> None:
            try:
                self.unbind_all("<KeyPress>")
            except Exception:
                pass
            self._cancel_capture = None
            display_text = (new_key or self._binds[config_key]).upper()
            button.configure(
                text=display_text,
                fg_color=theme.accent,
                hover_color=theme.accent_hover,
                text_color=theme.accent_on_accent,
            )
            self._capturing = False
            self._set_binding(False)

        self._cancel_capture = cleanup

        def on_key(event: tk.Event) -> str:
            keysym = (event.keysym or "").lower()
            if keysym in MODIFIER_KEYSYMS:
                return "break"
            if keysym == "escape":
                cleanup()
                return "break"

            if keysym in SPECIAL_KEYSYM_MAP:
                key_name = SPECIAL_KEYSYM_MAP[keysym]
            elif len(keysym) == 1:
                key_name = keysym
            elif event.char and event.char.isprintable() and not event.char.isspace():
                key_name = event.char.lower()
            else:
                key_name = keysym

            self._binds[config_key] = key_name
            cleanup(key_name)
            return "break"

        self.bind_all("<KeyPress>", on_key)
        self.focus_set()

    def _browse(self) -> None:
        path = filedialog.askdirectory()
        if path:
            self._dir_entry.delete(0, tk.END)
            self._dir_entry.insert(0, path)

    def _save(self) -> None:
        updated = replace(
            self._config,
            theme=theme_id_for_label(self._theme_var.get()),
            show_now_playing=self._now_playing_var.get(),
            show_actions=self._actions_var.get(),
            hud_position=self._pos_var.get(),
            hud_timeout=REVERSE_TIMEOUT.get(self._time_var.get(), 2000),
            hud_song_timeout=REVERSE_TIMEOUT.get(self._song_time_var.get(), 3500),
            autopause_device=self._device_var.get(),
            enable_hardware_keys=self._hardware_var.get(),
            music_dir=self._dir_entry.get(),
            mod_key=self._mod_var.get().lower(),
            key_play=self._binds["key_play"],
            key_next=self._binds["key_next"],
            key_prev=self._binds["key_prev"],
            key_show_song=self._binds["key_show_song"],
            key_ignore=self._binds["key_ignore"],
            key_vol_up=self._binds["key_vol_up"],
            key_vol_down=self._binds["key_vol_down"],
            autostart=self._autostart_var.get(),
        )
        self._config = updated
        self._on_save(updated)
        new_theme = get_theme(updated.theme)
        self.apply_theme(new_theme)

        # Immediate visual confirmation on the save button
        self._save_btn.configure(text="✓ Saved!", fg_color="#2ecc71", hover_color="#27ae60")
        self.after(
            1500,
            lambda: self._save_btn.configure(
                text="Save & Apply",
                fg_color=self._theme.accent,
                hover_color=self._theme.accent_hover,
                text_color=self._theme.accent_on_accent,
            ),
        )

    def _destroy(self) -> None:
        if self._cancel_capture is not None:
            try:
                self._cancel_capture()
            except Exception:
                pass
        self._capturing = False
        self._set_binding(False)
        try:
            self.unbind_all("<KeyPress>")
        except Exception:
            pass
        try:
            geo = self.geometry()
        except Exception:
            geo = None
        self._on_close(geo)
        self.destroy()
