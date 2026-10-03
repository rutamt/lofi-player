"""Turn VLC MRL file paths into title-case display names."""

from __future__ import annotations

import os
import re
import urllib.parse
import urllib.request
from typing import Optional


def mrl_to_local_path(mrl: Optional[str]) -> Optional[str]:
    if not mrl:
        return None
    parsed = urllib.parse.urlparse(mrl)
    return urllib.request.url2pathname(parsed.path)


def clean_title_from_filename(filename: str) -> str:
    display_name = os.path.splitext(filename)[0]

    # Strip common downloader/ripper prefixes
    display_name = re.sub(
        r"^(y2mate\.com|ytmp3\.cc|snaptik)\s*[-_]?\s*",
        "",
        display_name,
        flags=re.IGNORECASE,
    )

    # Strip leading track numbers like "01 - ", "01. ", "1. "
    display_name = re.sub(r"^\d{1,3}\s*[\.\-_]\s*", "", display_name)

    # Strip noisy tags in brackets / parentheses
    noise_patterns = [
        r"\((?:official\s*(?:video|audio|music\s*video)|visualizer|lyrics|audio|320\s*kbps|hq|hd|4k)\)",
        r"\[(?:official\s*(?:video|audio|music\s*video)|visualizer|lyrics|audio|320\s*kbps|flac|hq|hd|4k|lofi\s*(?:beats|hip\s*hop|chill)?)\]",
    ]
    for pattern in noise_patterns:
        display_name = re.sub(pattern, "", display_name, flags=re.IGNORECASE)

    # Clean up all underscores and hyphens into clean spaces
    display_name = re.sub(r"[-_]+", " ", display_name)
    display_name = re.sub(r"\s+", " ", display_name).strip()
    return display_name.title() if display_name else "Unknown Track"


def clean_title_from_mrl(mrl: Optional[str]) -> Optional[str]:
    local_path = mrl_to_local_path(mrl)
    if not local_path:
        return None
    return clean_title_from_filename(os.path.basename(local_path))
