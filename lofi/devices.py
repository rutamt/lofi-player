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
    """Enumerate output audio devices on macOS using fast in-memory CoreAudio query."""
    devices: List[str] = []

    # Fast path: query CoreAudio framework in-memory (< 0.1ms, zero subprocesses)
    try:
        import ctypes
        import ctypes.util

        core_audio_path = ctypes.util.find_library("CoreAudio")
        if core_audio_path:
            core_audio = ctypes.cdll.LoadLibrary(core_audio_path)

            class AudioObjectPropertyAddress(ctypes.Structure):
                _fields_ = [
                    ("mSelector", ctypes.c_uint32),
                    ("mScope", ctypes.c_uint32),
                    ("mElement", ctypes.c_uint32),
                ]

            # kAudioHardwarePropertyDevices = 'dev#' (0x64657623), kAudioObjectPropertyScopeGlobal = 'glob' (0x676c6f62)
            prop_devices = AudioObjectPropertyAddress(0x64657623, 0x676c6f62, 0)
            data_size = ctypes.c_uint32(0)
            if core_audio.AudioObjectGetPropertyDataSize(1, ctypes.byref(prop_devices), 0, None, ctypes.byref(data_size)) == 0:
                num_devices = data_size.value // ctypes.sizeof(ctypes.c_uint32)
                device_ids = (ctypes.c_uint32 * num_devices)()
                if core_audio.AudioObjectGetPropertyData(1, ctypes.byref(prop_devices), 0, None, ctypes.byref(data_size), ctypes.byref(device_ids)) == 0:
                    for dev_id in device_ids:
                        # kAudioDevicePropertyStreams = 'stm#' (0x73746d23), kAudioObjectPropertyScopeOutput = 'outp' (0x6f757470)
                        prop_stms = AudioObjectPropertyAddress(0x73746d23, 0x6f757470, 0)
                        stms_size = ctypes.c_uint32(0)
                        err = core_audio.AudioObjectGetPropertyDataSize(dev_id, ctypes.byref(prop_stms), 0, None, ctypes.byref(stms_size))
                        if err == 0 and stms_size.value > 0:
                            # Has output streams -> query device name: kAudioObjectPropertyName = 'name' (0x6e616d65)
                            prop_name = AudioObjectPropertyAddress(0x6e616d65, 0x676c6f62, 0)
                            name_buf = ctypes.create_string_buffer(256)
                            name_size = ctypes.c_uint32(256)
                            if core_audio.AudioObjectGetPropertyData(dev_id, ctypes.byref(prop_name), 0, None, ctypes.byref(name_size), name_buf) == 0:
                                name = name_buf.value.decode("utf-8", errors="ignore").strip()
                                if name and name not in devices:
                                    devices.append(name)
            if devices:
                return devices
    except Exception:
        pass

    # Fallback to system_profiler only if CoreAudio query is unavailable
    try:
        import json
        import subprocess

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
