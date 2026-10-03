"""Enumerate active Windows audio render endpoints via the registry."""

from __future__ import annotations

import winreg
from typing import List

RENDER_PATH = r"SOFTWARE\Microsoft\Windows\CurrentVersion\MMDevices\Audio\Render"
DEVICE_NAME_PROPERTY = "{b3f8fa53-0004-438e-9003-51a46e139bfc},6"
DEVICE_STATE_ACTIVE = 1


def get_active_audio_devices() -> List[str]:
    """Return friendly names of active render devices.

    Reads ``HKLM\\...\\MMDevices\\Audio\\Render`` directly. COM wrappers such as
    pycaw fail silently inside a frozen PyInstaller executable.
    """
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
