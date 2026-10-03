"""Tabbed CustomTkinter settings window."""

from __future__ import annotations

import os
from dataclasses import replace
from typing import Callable, Dict, List, Optional

import customtkinter as ctk
import tkinter as tk
from pynput import keyboard
from tkinter import filedialog

from lofi.config import AppConfig
from lofi.paths import icon_path
from lofi.themes import Theme, get_theme, theme_id_for_label, theme_labels

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
            x = max(0, (sw - 640) // 2)
            y = max(0, (sh - 720) // 2)
            self.geometry(f"640x720+{x}+{y}")
        self.minsize(600, 640)
        self.protocol("WM_DELETE_WINDOW", self._destroy)

        icon = icon_path()
        if os.path.exists(icon):
            self.after(200, lambda: self._try_icon(icon))

        theme = self._theme
        self.configure(fg_color=theme.bg)

        outer = ctk.CTkFrame(self, fg_color="transparent")
        outer.pack(fill="both", expand=True, padx=20, pady=20)
        outer.grid_rowconfigure(1, weight=1)
        outer.grid_columnconfigure(0, weight=1)

        header = ctk.CTkFrame(outer, fg_color="transparent")
        header.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        self._header_title = ctk.CTkLabel(
            header,
            text="LoFi HUD",
            font=("Segoe UI", 24, "bold"),
            text_color=theme.fg,
        )
        self._header_title.pack(anchor="w")
        self._header_sub = ctk.CTkLabel(
            header,
            text="Playback, overlay, and hotkeys",
            font=("Segoe UI", 13),
            text_color=theme.muted,
        )
        self._header_sub.pack(anchor="w", pady=(2, 0))

        self._tabs = ctk.CTkTabview(
            outer,
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
        self._tabs.grid(row=1, column=0, sticky="nsew")
        self._tabs.add("Appearance")
        self._tabs.add("Playback")
        self._tabs.add("Controls")

        self._build_appearance(self._tabs.tab("Appearance"))
        self._build_playback(self._tabs.tab("Playback"), get_devices())
        self._build_controls(self._tabs.tab("Controls"))

        footer = ctk.CTkFrame(outer, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        self._save_btn = ctk.CTkButton(
            footer,
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
        self._footer_lbl = ctk.CTkLabel(
            footer,
            text=f"LoFi HUD v{__version__} • Created by Rutam and Gemini",
            font=("Segoe UI", 11),
            text_color=theme.muted,
        )
        self._footer_lbl.pack(pady=(8, 0))

    def apply_theme(self, theme: Theme) -> None:
        """Dynamically re-color all widgets in-place without closing or flickering."""
        self._theme = theme
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
        )

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

        self._save_btn.configure(
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
        )
        self._footer_lbl.configure(text_color=theme.muted)

    def _try_icon(self, path: str) -> None:
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

    def _row(self, parent: tk.Misc, label: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
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

    def _switch(self, parent: tk.Misc, text: str, variable: ctk.BooleanVar, pady: Tuple[int, int] = (0, 8)) -> ctk.CTkSwitch:
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
        self._theme_var = ctk.StringVar(value=theme.label)
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

        self._switch(card, "Start LoFi HUD with Windows", self._autostart_var, pady=(4, 8))
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
        dir_frame = ctk.CTkFrame(source, fg_color="transparent")
        dir_frame.pack(fill="x", padx=PAD, pady=(4, 8))
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

        action_frame = ctk.CTkFrame(source, fg_color="transparent")
        action_frame.pack(fill="x", padx=PAD, pady=(0, PAD))

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

    def _open_folder_action(self) -> None:
        path = self._dir_entry.get().strip()
        if not path:
            return
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            os.startfile(path)
        except Exception:
            pass

    def _build_controls(self, parent: tk.Misc) -> None:
        config = self._config
        card = self._card(parent, "Keybinds")

        self._hardware_var = ctk.BooleanVar(value=config.enable_hardware_keys)
        self._switch(card, "Enable hardware media keys", self._hardware_var, pady=(4, 8))

        row = self._row(card, "Hold Modifier")
        self._mod_var = ctk.StringVar(value=config.mod_key.upper())
        self._menu(row, self._mod_var, ["ALT", "CTRL", "SHIFT"], width=160)

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
        if self._capturing:
            return
        self._capturing = True
        theme = self._theme
        self._set_binding(True)
        button.configure(
            text="Listening...",
            fg_color=theme.danger,
            hover_color=theme.danger_hover,
            text_color="#ffffff",
        )

        def capture_key(key: object) -> bool:
            try:
                key_name = key.char if getattr(key, "char", None) else getattr(key, "name", None)
            except AttributeError:
                key_name = str(key).replace("Key.", "")
            key_name = str(key_name).lower()
            self._binds[config_key] = key_name

            def restore() -> None:
                button.configure(
                    text=key_name.upper(),
                    fg_color=theme.accent,
                    hover_color=theme.accent_hover,
                    text_color=theme.accent_on_accent,
                )
                self._capturing = False
                self._set_binding(False)

            self.after(0, restore)
            return False

        keyboard.Listener(on_press=capture_key).start()

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
        self._capturing = False
        self._set_binding(False)
        try:
            geo = self.geometry()
        except Exception:
            geo = None
        self._on_close(geo)
        self.destroy()
