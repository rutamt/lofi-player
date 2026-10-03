"""Headless VLC playback: shuffled local library, loop, ignore-song."""

from __future__ import annotations

import os
import random
import shutil
from typing import List, Optional

from lofi.names import clean_title_from_mrl, mrl_to_local_path
from lofi.paths import application_dir, ignored_dir_for

VALID_EXTENSIONS = (
    ".mp3",
    ".wav",
    ".flac",
    ".ogg",
    ".m4a",
    ".aac",
    ".opus",
    ".wma",
)
VLC_CANDIDATES = (
    r"C:\Program Files\VideoLAN\VLC",
    r"C:\Program Files (x86)\VideoLAN\VLC",
)


def find_vlc_dir() -> Optional[str]:
    # Check bundled/portable paths first
    base = application_dir()
    local_candidates = [
        base,
        os.path.join(base, "vlc"),
        os.path.join(base, "_internal"),
        os.path.join(base, "_internal", "vlc"),
    ]
    for path in local_candidates:
        if os.path.exists(os.path.join(path, "libvlc.dll")):
            return path

    # Check system installation candidates
    for path in VLC_CANDIDATES:
        if os.path.exists(path):
            return path
    return None


def configure_vlc_env() -> Optional[str]:
    """Point python-vlc at a local VLC install. Returns the install dir or None."""
    vlc_dir = find_vlc_dir()
    if not vlc_dir:
        return None
    os.environ["PYTHON_VLC_MODULE_PATH"] = vlc_dir
    os.environ["PYTHON_VLC_LIB_PATH"] = os.path.join(vlc_dir, "libvlc.dll")
    os.environ["PATH"] = vlc_dir + os.pathsep + os.environ.get("PATH", "")
    return vlc_dir


class Player:
    """VLC MediaListPlayer wrapper. Mutate only from the Tk thread."""

    def __init__(self, volume: int = 50) -> None:
        self.song_paths: List[str] = []
        self.is_playing = False
        self.available = False
        self._instance = None
        self._list_player = None
        self._media_player = None

        vlc_dir = configure_vlc_env()
        if not vlc_dir:
            return

        try:
            import vlc
        except (OSError, ImportError):
            return

        plugin_path = os.path.join(vlc_dir, "plugins")
        try:
            self._instance = vlc.Instance(
                "--no-video",
                "--no-stats",
                "--no-sub-autodetect-file",
                "--no-osd",
                "--quiet",
                "--plugin-path={}".format(plugin_path),
            )
            self._list_player = self._instance.media_list_player_new()
            self._media_player = self._list_player.get_media_player()
            self._media_player.audio_set_volume(max(0, min(100, volume)))
            self.available = True
        except Exception:
            self.available = False

    def load_library(self, music_dir: str) -> None:
        """Scan ``music_dir``, skip Ignored_Lofi, shuffle, and loop the list."""
        if not self.available:
            self.song_paths = []
            return

        import vlc

        self._list_player.stop()
        media_list = self._instance.media_list_new()
        self.song_paths = []

        if os.path.exists(music_dir):
            for root_dir, _dirs, files in os.walk(music_dir):
                if "Ignored_Lofi" in root_dir:
                    continue
                for filename in files:
                    if filename.lower().endswith(VALID_EXTENSIONS):
                        self.song_paths.append(os.path.join(root_dir, filename))

        if self.song_paths:
            random.shuffle(self.song_paths)
            for path in self.song_paths:
                media_list.add_media(self._instance.media_new(path))

        self._list_player.set_media_list(media_list)
        self._list_player.set_playback_mode(vlc.PlaybackMode.loop)
        self.is_playing = False

    def current_mrl(self) -> Optional[str]:
        if not self.available:
            return None
        media = self._media_player.get_media()
        if not media:
            return None
        return media.get_mrl()

    def clean_name(self) -> Optional[str]:
        return clean_title_from_mrl(self.current_mrl())

    def local_path(self) -> Optional[str]:
        return mrl_to_local_path(self.current_mrl())

    def is_media_playing(self) -> bool:
        if not self.available:
            return False
        import vlc

        return self._list_player.get_state() == vlc.State.Playing

    def play(self) -> bool:
        if not self.available or not self.song_paths or self.is_playing:
            return False
        self._list_player.play()
        self.is_playing = True
        return True

    def pause(self) -> bool:
        if not self.available or not self.is_playing:
            return False
        self._list_player.pause()
        self.is_playing = False
        return True

    def toggle(self) -> str:
        """Return ``play``, ``pause``, ``empty``, or ``unavailable``."""
        if not self.available:
            return "unavailable"
        if not self.song_paths:
            return "empty"
        if self.is_playing:
            self.pause()
            return "pause"
        self.play()
        return "play"

    def next(self) -> bool:
        if not self.available or not self.song_paths:
            return False
        self._list_player.next()
        self.is_playing = True
        return True

    def previous(self) -> bool:
        if not self.available or not self.song_paths:
            return False
        self._list_player.previous()
        self.is_playing = True
        return True

    def set_volume(self, volume: int) -> int:
        clamped = max(0, min(100, volume))
        if self.available:
            self._media_player.audio_set_volume(clamped)
        return clamped

    def ignore_current(self, music_dir: str) -> Optional[str]:
        """Move the current file to Ignored_Lofi and skip to the next track."""
        local_path = self.local_path()
        song_name = self.clean_name()
        if not local_path or not os.path.exists(local_path):
            return None

        ignored = ignored_dir_for(music_dir)
        try:
            if not os.path.exists(ignored):
                os.makedirs(ignored)
            dest_path = os.path.join(ignored, os.path.basename(local_path))
            shutil.move(local_path, dest_path)
        except OSError:
            return None

        if local_path in self.song_paths:
            self.song_paths.remove(local_path)
        self.next()
        return song_name

    def stop(self) -> None:
        if self.available:
            try:
                self._list_player.stop()
            except Exception:
                pass
        self.is_playing = False
