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
    display_name = re.sub(r"[-_]", " ", display_name)
    return re.sub(r"\s+", " ", display_name).strip().title()


def clean_title_from_mrl(mrl: Optional[str]) -> Optional[str]:
    local_path = mrl_to_local_path(mrl)
    if not local_path:
        return None
    return clean_title_from_filename(os.path.basename(local_path))
