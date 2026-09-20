"""Tokenized color palettes for Settings and the HUD overlay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List


@dataclass(frozen=True)
class Theme:
    """Cohesive palette applied to CustomTkinter widgets and the HUD."""

    id: str
    label: str
    appearance: str
    bg: str
    surface: str
    surface_alt: str
    border: str
    fg: str
    muted: str
    accent: str
    accent_hover: str
    accent_on_accent: str
    hud_bg: str
    hud_fg: str
    danger: str
    danger_hover: str


THEMES: Dict[str, Theme] = {
    "harbor_night": Theme(
        id="harbor_night",
        label="Harbor Night",
        appearance="dark",
        bg="#1e1e2e",
        surface="#252536",
        surface_alt="#2c2c40",
        border="#35354a",
        fg="#e8eaf0",
        muted="#8b90a5",
        accent="#4a90e2",
        accent_hover="#357abd",
        accent_on_accent="#ffffff",
        hud_bg="#1e1e2e",
        hud_fg="#4a90e2",
        danger="#e63946",
        danger_hover="#c1121f",
    ),
    "tokyo_night": Theme(
        id="tokyo_night",
        label="Tokyo Night",
        appearance="dark",
        bg="#1a1b26",
        surface="#24283b",
        surface_alt="#2f354a",
        border="#3b4261",
        fg="#c0caf5",
        muted="#7aa2f7",
        accent="#bb9af7",
        accent_hover="#9d7cd8",
        accent_on_accent="#1a1b26",
        hud_bg="#1a1b26",
        hud_fg="#bb9af7",
        danger="#f7768e",
        danger_hover="#db4b4b",
    ),
    "rose_pine": Theme(
        id="rose_pine",
        label="Rosé Pine",
        appearance="dark",
        bg="#191724",
        surface="#21202e",
        surface_alt="#26233a",
        border="#393552",
        fg="#e0def4",
        muted="#908caa",
        accent="#eb6f92",
        accent_hover="#d7827e",
        accent_on_accent="#191724",
        hud_bg="#191724",
        hud_fg="#eb6f92",
        danger="#eb6f92",
        danger_hover="#b4637a",
    ),
    "polar_dusk": Theme(
        id="polar_dusk",
        label="Polar Dusk",
        appearance="dark",
        bg="#2e3440",
        surface="#3b4252",
        surface_alt="#434c5e",
        border="#4c566a",
        fg="#eceff4",
        muted="#81a1c1",
        accent="#88c0d0",
        accent_hover="#5e81ac",
        accent_on_accent="#2e3440",
        hud_bg="#2e3440",
        hud_fg="#88c0d0",
        danger="#bf616a",
        danger_hover="#a54e56",
    ),
    "gruvbox": Theme(
        id="gruvbox",
        label="Gruvbox Warm",
        appearance="dark",
        bg="#282828",
        surface="#32302f",
        surface_alt="#3c3836",
        border="#504945",
        fg="#ebdbb2",
        muted="#a89984",
        accent="#fe8019",
        accent_hover="#d65d0e",
        accent_on_accent="#282828",
        hud_bg="#282828",
        hud_fg="#fe8019",
        danger="#fb4934",
        danger_hover="#cc241d",
    ),
    "latte": Theme(
        id="latte",
        label="Catppuccin Latte",
        appearance="light",
        bg="#eff1f5",
        surface="#ffffff",
        surface_alt="#e6e9ef",
        border="#ccd0da",
        fg="#4c4f69",
        muted="#8c8fa1",
        accent="#8839ef",
        accent_hover="#7287fd",
        accent_on_accent="#ffffff",
        hud_bg="#eff1f5",
        hud_fg="#8839ef",
        danger="#d20f39",
        danger_hover="#e64553",
    ),
}

DEFAULT_THEME_ID = "harbor_night"

_LEGACY_THEME_NAMES = {
    "Midnight Blue": "harbor_night",
    "Nordic Clean": "polar_dusk",
    "Forest Glow": "gruvbox",
    "Cherry Blossom": "rose_pine",
    "Minimal Light": "latte",
    "Cyberpunk": "tokyo_night",
    "Harbor Night": "harbor_night",
    "Polar Dusk": "polar_dusk",
    "Canopy": "gruvbox",
    "Hanami": "rose_pine",
    "Paper": "latte",
    "Circuit": "tokyo_night",
    "Tokyo Night": "tokyo_night",
    "Rosé Pine": "rose_pine",
    "Gruvbox Warm": "gruvbox",
    "Catppuccin Latte": "latte",
    "canopy": "gruvbox",
    "hanami": "rose_pine",
    "paper": "latte",
    "circuit": "tokyo_night",
}


def resolve_theme_id(value: str | None) -> str:
    """Map a stored theme id or legacy display name onto a known palette."""
    if not value:
        return DEFAULT_THEME_ID
    if value in THEMES:
        return value
    mapped = _LEGACY_THEME_NAMES.get(value)
    if mapped and mapped in THEMES:
        return mapped
    return DEFAULT_THEME_ID


def get_theme(theme_id: str | None) -> Theme:
    return THEMES[resolve_theme_id(theme_id)]


def theme_labels() -> List[str]:
    return [theme.label for theme in THEMES.values()]


def theme_id_for_label(label: str) -> str:
    for theme in THEMES.values():
        if theme.label == label:
            return theme.id
    mapped = _LEGACY_THEME_NAMES.get(label)
    if mapped and mapped in THEMES:
        return mapped
    return DEFAULT_THEME_ID
