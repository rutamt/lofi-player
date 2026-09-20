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
    """Owns the singleton settings Toplevel."""

    def __init__(
        self,
        root: ctk.CTk,
        get_config: Callable[[], AppConfig],
        save_config: Callable[[AppConfig], None],
        get_devices: Callable[[], List[str]],
        set_binding: Callable[[bool], None],
    ) -> None:
        self._root = root
        self._get_config = get_config
        self._save_config = save_config
        self._get_devices = get_devices
        self._set_binding = set_binding
        self._window: Optional[ctk.CTkToplevel] = None

    def open(self) -> None:
        if self._window is not None and self._window.winfo_exists():
            self._window.focus()
            return
        self._window = SettingsWindow(
            self._root,
            self._get_config(),
            self._save_config,
            self._get_devices,
            self._set_binding,
            on_close=self._on_close,
        )

    def _on_close(self) -> None:
        self._window = None


class SettingsWindow(ctk.CTkToplevel):
    def __init__(
        self,
        root: ctk.CTk,
        config: AppConfig,
        on_save: Callable[[AppConfig], None],
        get_devices: Callable[[], List[str]],
        set_binding: Callable[[bool], None],
        on_close: Callable[[], None],
    ) -> None:
        super().__init__(root)
        self._config = config
        self._on_save = on_save
        self._set_binding = set_binding
        self._on_close = on_close
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

        self.title("LoFi HUD Settings")
        self.geometry("640x720")
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
        ctk.CTkLabel(
            header,
            text="LoFi HUD",
            font=("Segoe UI", 24, "bold"),
            text_color=theme.fg,
        ).pack(anchor="w")
        ctk.CTkLabel(
            header,
            text="Playback, overlay, and hotkeys",
            font=("Segoe UI", 13),
            text_color=theme.muted,
        ).pack(anchor="w", pady=(2, 0))

        unselected = theme.muted if theme.appearance == "light" else theme.surface_alt
        tabs = ctk.CTkTabview(
            outer,
            corner_radius=CARD_RADIUS,
            fg_color=theme.surface,
            segmented_button_fg_color=theme.surface_alt,
            segmented_button_selected_color=theme.accent,
            segmented_button_selected_hover_color=theme.accent_hover,
            segmented_button_unselected_color=unselected,
            segmented_button_unselected_hover_color=theme.border,
            text_color="#fafafa",
            text_color_disabled=theme.muted,
        )
        tabs.grid(row=1, column=0, sticky="nsew")
        tabs.add("Appearance")
        tabs.add("Playback")
        tabs.add("Controls")

        self._build_appearance(tabs.tab("Appearance"))
        self._build_playback(tabs.tab("Playback"), get_devices())
        self._build_controls(tabs.tab("Controls"))

        footer = ctk.CTkFrame(outer, fg_color="transparent")
        footer.grid(row=2, column=0, sticky="ew", pady=(16, 0))
        ctk.CTkButton(
            footer,
            text="Save & Apply",
            command=self._save,
            font=("Segoe UI", 14, "bold"),
            height=42,
            corner_radius=10,
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
        ).pack(fill="x")
        ctk.CTkLabel(
            footer,
            text="Created by Tasga & Gemini",
            font=("Segoe UI", 11),
            text_color=theme.muted,
        ).pack(pady=(8, 0))

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
        ctk.CTkLabel(
            card,
            text=title,
            font=("Segoe UI", 14, "bold"),
            text_color=theme.fg,
        ).pack(anchor="w", padx=PAD, pady=(PAD, 6))
        return card

    def _row(self, parent: tk.Misc, label: str) -> ctk.CTkFrame:
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.pack(fill="x", padx=PAD, pady=6)
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            row,
            text=label,
            width=LABEL_WIDTH,
            anchor="w",
            font=("Segoe UI", 12),
            text_color=self._theme.fg,
        ).grid(row=0, column=0, sticky="w")
        return row

    def _menu(self, parent: tk.Misc, variable: ctk.StringVar, values: List[str], width: int = CONTROL_WIDTH) -> ctk.CTkOptionMenu:
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
        )
        menu.grid(row=0, column=1, sticky="e")
        return menu

    def _build_appearance(self, parent: tk.Misc) -> None:
        config = self._config
        theme = get_theme(config.theme)
        card = self._card(parent, "Theme & overlay")

        row = self._row(card, "Active Theme")
        self._theme_var = ctk.StringVar(value=theme.label)
        self._menu(row, self._theme_var, theme_labels())

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
        theme = self._theme
        card = self._card(parent, "Behavior")

        self._now_playing_var = ctk.BooleanVar(value=config.show_now_playing)
        self._actions_var = ctk.BooleanVar(value=config.show_actions)
        ctk.CTkSwitch(
            card,
            text="Auto-show Now Playing when the track changes",
            variable=self._now_playing_var,
            progress_color=theme.accent,
            button_color=theme.fg,
            font=("Segoe UI", 12),
            text_color=theme.fg,
        ).pack(anchor="w", padx=PAD, pady=(4, 8))
        ctk.CTkSwitch(
            card,
            text="Show volume and play/pause HUD",
            variable=self._actions_var,
            progress_color=theme.accent,
            button_color=theme.fg,
            font=("Segoe UI", 12),
            text_color=theme.fg,
        ).pack(anchor="w", padx=PAD, pady=(0, 8))

        opts = ["Disabled"] + devices
        if config.autopause_device not in opts:
            opts.append(config.autopause_device)
        row = self._row(card, "Auto-Pause Device")
        self._device_var = ctk.StringVar(value=config.autopause_device)
        self._menu(row, self._device_var, opts)
        ctk.CTkFrame(card, height=12, fg_color="transparent").pack()

        source = self._card(parent, "Music source")
        dir_frame = ctk.CTkFrame(source, fg_color="transparent")
        dir_frame.pack(fill="x", padx=PAD, pady=(4, PAD))
        self._dir_entry = ctk.CTkEntry(
            dir_frame,
            fg_color=theme.surface,
            border_color=theme.border,
            text_color=theme.fg,
        )
        self._dir_entry.insert(0, config.music_dir)
        self._dir_entry.pack(side="left", fill="x", expand=True, padx=(0, 10))
        ctk.CTkButton(
            dir_frame,
            text="Browse",
            width=88,
            fg_color=theme.accent,
            hover_color=theme.accent_hover,
            text_color=theme.accent_on_accent,
            command=self._browse,
        ).pack(side="right")

    def _build_controls(self, parent: tk.Misc) -> None:
        config = self._config
        theme = self._theme
        card = self._card(parent, "Keybinds")

        self._hardware_var = ctk.BooleanVar(value=config.enable_hardware_keys)
        ctk.CTkSwitch(
            card,
            text="Enable hardware media keys",
            variable=self._hardware_var,
            progress_color=theme.accent,
            button_color=theme.fg,
            font=("Segoe UI", 12),
            text_color=theme.fg,
        ).pack(anchor="w", padx=PAD, pady=(4, 8))

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
        )
        self._on_save(updated)
        self._destroy()

    def _destroy(self) -> None:
        self._capturing = False
        self._set_binding(False)
        self._on_close()
        self.destroy()
