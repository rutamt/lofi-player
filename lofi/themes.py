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
    "polar_dusk": Theme(
        id="polar_dusk",
        label="Polar Dusk",
        appearance="dark",
        bg="#2e3440",
        surface="#3b4252",
        surface_alt="#434c5e",
        border="#4c566a",
        fg="#eceff4",
        muted="#a3b0c2",
        accent="#88c0d0",
        accent_hover="#81a1c1",
        accent_on_accent="#2e3440",
        hud_bg="#2e3440",
        hud_fg="#88c0d0",
        danger="#bf616a",
        danger_hover="#a54e56",
    ),
    "canopy": Theme(
        id="canopy",
        label="Canopy",
        appearance="dark",
        bg="#1c2520",
        surface="#24302a",
        surface_alt="#2c3a32",
        border="#35463c",
        fg="#e6f0ea",
        muted="#8aa394",
        accent="#2ecc71",
        accent_hover="#27ae60",
        accent_on_accent="#0d1a12",
        hud_bg="#1c2520",
        hud_fg="#2ecc71",
        danger="#e74c3c",
        danger_hover="#c0392b",
    ),
    "hanami": Theme(
        id="hanami",
        label="Hanami",
        appearance="light",
        bg="#fff0f3",
        surface="#ffffff",
        surface_alt="#ffe4ea",
        border="#ffd0da",
        fg="#3b1f28",
        muted="#9a6b78",
        accent="#ff4d6d",
        accent_hover="#ff758f",
        accent_on_accent="#ffffff",
        hud_bg="#fff0f3",
        hud_fg="#ff4d6d",
        danger="#e63946",
        danger_hover="#c1121f",
    ),
    "paper": Theme(
        id="paper",
        label="Paper",
        appearance="light",
        bg="#f4f4f5",
        surface="#ffffff",
        surface_alt="#ececee",
        border="#d4d4d8",
        fg="#18181b",
        muted="#71717a",
        accent="#18181b",
        accent_hover="#3f3f46",
        accent_on_accent="#fafafa",
        hud_bg="#f4f4f5",
        hud_fg="#18181b",
        danger="#e63946",
        danger_hover="#c1121f",
    ),
    "circuit": Theme(
        id="circuit",
        label="Circuit",
        appearance="dark",
        bg="#09090b",
        surface="#121216",
        surface_alt="#1a1a22",
        border="#27272f",
        fg="#f4f4f5",
        muted="#a1a1aa",
        accent="#00f0ff",
        accent_hover="#d900ff",
        accent_on_accent="#09090b",
        hud_bg="#09090b",
        hud_fg="#00f0ff",
        danger="#ff2d55",
        danger_hover="#d900ff",
    ),
}

DEFAULT_THEME_ID = "harbor_night"

_LEGACY_THEME_NAMES = {
    "Midnight Blue": "harbor_night",
    "Nordic Clean": "polar_dusk",
    "Forest Glow": "canopy",
    "Cherry Blossom": "hanami",
    "Minimal Light": "paper",
    "Cyberpunk": "circuit",
    "Harbor Night": "harbor_night",
    "Polar Dusk": "polar_dusk",
    "Canopy": "canopy",
    "Hanami": "hanami",
    "Paper": "paper",
    "Circuit": "circuit",
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
    return DEFAULT_THEME_ID
