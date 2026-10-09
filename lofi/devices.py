"""Enumerate active audio render endpoints (Windows registry or macOS system_profiler)."""

from __future__ import annotations

import sys
from typing import List

RENDER_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
DEVICE_NAME_PROPERTY = "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"
DEVICE_STATE_ACTIVE = 1


def _get_windows_audio_devices() -> List[str]:
    """Reads HKLM\\...\\MMDevices\\Audio\\Render directly on Windows."""
    import winreg

    devices: List[str] = []
    try:
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, RENDER_PATH) as key:
            num_subkeys = winreg.QueryInfoKey(key)[0]
            for index in range(num_subkeys):
                try:
                    guid = winreg.EnumKey(key, index)
                    with winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE, "{}\\{}".format(RENDER_PATH, guid)
                    ) as dev_key:
                        state, _ = winreg.QueryValueEx(dev_key, "DeviceState")
                        if state != DEVICE_STATE_ACTIVE:
                            continue
                        with winreg.OpenKey(
                            winreg.HKEY_LOCAL_MACHINE,
                            "{}\\{}\\Properties".format(RENDER_PATH, guid),
                        ) as prop_key:
                            name, _ = winreg.QueryValueEx(prop_key, DEVICE_NAME_PROPERTY)
                            devices.append(name)
                except OSError:
                    continue
    except OSError:
        pass
    return devices


def _get_mac_audio_devices() -> List[str]:
    """Enumerate output audio devices on macOS using system_profiler."""
    import json
    import subprocess

    devices: List[str] = []
    try:
        res = subprocess.run(
            ["system_profiler", "SPAudioDataType", "-json"],
            capture_output=True,
            text=True,
            check=False,
            timeout=5,
        )
        if res.returncode == 0 and res.stdout:
            data = json.loads(res.stdout)
            for section in data.get("SPAudioDataType", []):
                for item in section.get("_items", []):
                    name = item.get("_name")
                    if name and ("coreaudio_output_streams" in item or "coreaudio_default_audio_output_device" in item):
                        if name not in devices:
                            devices.append(name)
    except Exception:
        pass
    return devices


def get_active_audio_devices() -> List[str]:
    """Return friendly names of active render devices."""
    if sys.platform == "win32":
        return _get_windows_audio_devices()
    elif sys.platform == "darwin":
        return _get_mac_audio_devices()
    return []
