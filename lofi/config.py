"""Load, merge, and persist application configuration."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, fields, replace
from typing import Any, Dict, Optional

from lofi.paths import config_path, default_music_dir
from lofi.themes import DEFAULT_THEME_ID, resolve_theme_id


@dataclass
class AppConfig:
    music_dir: str
    mod_key: str
    key_play: str
    key_next: str
    key_prev: str
    key_show_song: str
    key_ignore: str
    key_vol_up: str
    key_vol_down: str
    volume: int
    show_now_playing: bool
    show_actions: bool
    hud_position: str
    hud_timeout: int
    hud_song_timeout: int
    autopause_device: str
    enable_hardware_keys: bool
    theme: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


_FIELD_NAMES = {item.name for item in fields(AppConfig)}


def default_config() -> AppConfig:
    return AppConfig(
        music_dir=default_music_dir(),
        mod_key="alt",
        key_play="q",
        key_next="2",
        key_prev="1",
        key_show_song="3",
        key_ignore="4",
        key_vol_up="up",
        key_vol_down="down",
        volume=50,
        show_now_playing=True,
        show_actions=True,
        hud_position="Bottom Center",
        hud_timeout=2000,
        hud_song_timeout=3500,
        autopause_device="Disabled",
        enable_hardware_keys=True,
        theme=DEFAULT_THEME_ID,
    )


def _normalize(data: Dict[str, Any], base: Optional[AppConfig] = None) -> AppConfig:
    merged = default_config() if base is None else replace(base)
    known = {key: value for key, value in data.items() if key in _FIELD_NAMES}
    if known:
        merged = replace(merged, **known)
    merged.theme = resolve_theme_id(str(merged.theme) if merged.theme else None)
    merged.mod_key = str(merged.mod_key).lower()
    try:
        merged.volume = max(0, min(100, int(merged.volume)))
    except (TypeError, ValueError):
        merged.volume = 50
    return merged


def load_config(path: Optional[str] = None) -> AppConfig:
    """Return defaults merged with `config.json`. Corrupt files keep defaults."""
    target = path or config_path()
    if not os.path.exists(target):
        return default_config()
    try:
        with open(target, "r", encoding="utf-8") as handle:
            loaded = json.load(handle)
        if not isinstance(loaded, dict):
            return default_config()
        return _normalize(loaded)
    except (OSError, json.JSONDecodeError, TypeError, ValueError):
        bak = target + ".bak"
        try:
            if os.path.exists(target) and not os.path.exists(bak):
                os.replace(target, bak)
        except OSError:
            pass
        return default_config()


def save_config(config: AppConfig, path: Optional[str] = None) -> None:
    """Atomically write configuration next to the application executable."""
    target = path or config_path()
    payload = config.to_dict()
    payload["theme"] = resolve_theme_id(config.theme)
    directory = os.path.dirname(target)
    if directory and not os.path.exists(directory):
        os.makedirs(directory)
    tmp_path = target + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=4)
    os.replace(tmp_path, target)
