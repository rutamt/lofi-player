"""Single instance mutex and activation signaling for Windows."""

from __future__ import annotations

import ctypes
import threading
from ctypes import wintypes
from typing import Callable, Optional

# Win32 Error Codes and Constants
ERROR_ALREADY_EXISTS = 183
EVENT_MODIFY_STATE = 0x0002
WAIT_OBJECT_0 = 0x00000000
INFINITE = 0xFFFFFFFF

MUTEX_NAME = "Local\\LoFiHUD_SingleInstance_Mutex"
EVENT_NAME = "Local\\LoFiHUD_ActivateEvent"


class SingleInstance:
    """Ensures only a single instance of LoFi HUD runs per user session."""

    def __init__(
        self,
        mutex_name: str = MUTEX_NAME,
        event_name: str = EVENT_NAME,
    ) -> None:
        self.mutex_name = mutex_name
        self.event_name = event_name
        self._mutex_handle: Optional[int] = None
        self._event_handle: Optional[int] = None
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None

        self._kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        self._setup_prototypes()

    def _setup_prototypes(self) -> None:
        self._kernel32.CreateMutexW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        self._kernel32.CreateMutexW.restype = wintypes.HANDLE

        self._kernel32.CreateEventW.argtypes = [
            ctypes.c_void_p,
            wintypes.BOOL,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        self._kernel32.CreateEventW.restype = wintypes.HANDLE

        self._kernel32.OpenEventW.argtypes = [
            wintypes.DWORD,
            wintypes.BOOL,
            wintypes.LPCWSTR,
        ]
        self._kernel32.OpenEventW.restype = wintypes.HANDLE

        self._kernel32.SetEvent.argtypes = [wintypes.HANDLE]
        self._kernel32.SetEvent.restype = wintypes.BOOL

        self._kernel32.WaitForSingleObject.argtypes = [
            wintypes.HANDLE,
            wintypes.DWORD,
        ]
        self._kernel32.WaitForSingleObject.restype = wintypes.DWORD

        self._kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        self._kernel32.CloseHandle.restype = wintypes.BOOL

    def acquire(self) -> bool:
        """Attempt to acquire the named mutex.

        Returns True if this is the primary instance, False if an instance is already running.
        """
        try:
            self._mutex_handle = self._kernel32.CreateMutexW(None, False, self.mutex_name)
            last_err = ctypes.get_last_error()
            if last_err == ERROR_ALREADY_EXISTS:
                if self._mutex_handle:
                    self._kernel32.CloseHandle(self._mutex_handle)
                    self._mutex_handle = None
                return False
            return bool(self._mutex_handle)
        except Exception:
            return True

    def notify_running_instance(self) -> None:
        """Signal the existing instance to surface its interface."""
        try:
            event = self._kernel32.OpenEventW(EVENT_MODIFY_STATE, False, self.event_name)
            if event:
                self._kernel32.SetEvent(event)
                self._kernel32.CloseHandle(event)
        except Exception:
            pass

    def listen_for_activation(self, callback: Callable[[], None]) -> None:
        """Create the activation event and listen for signals from subsequent instances."""
        try:
            # Auto-reset event: resets to non-signaled once a waiting thread is released
            self._event_handle = self._kernel32.CreateEventW(None, False, False, self.event_name)
            if not self._event_handle:
                return

            self._listening = True

            def _listener() -> None:
                while self._listening:
                    res = self._kernel32.WaitForSingleObject(self._event_handle, 1000)
                    if res == WAIT_OBJECT_0:
                        try:
                            callback()
                        except Exception:
                            pass

            self._listen_thread = threading.Thread(target=_listener, daemon=True)
            self._listen_thread.start()
        except Exception:
            pass

    def release(self) -> None:
        """Release and close all Win32 synchronization handles."""
        self._listening = False
        if self._event_handle:
            try:
                self._kernel32.CloseHandle(self._event_handle)
            except Exception:
                pass
            self._event_handle = None

        if self._mutex_handle:
            try:
                self._kernel32.CloseHandle(self._mutex_handle)
            except Exception:
                pass
            self._mutex_handle = None
