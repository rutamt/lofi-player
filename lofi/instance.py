import os
import socket
import sys
import threading
from typing import Callable, Optional

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    ERROR_ALREADY_EXISTS = 183
    EVENT_MODIFY_STATE = 0x0002
    WAIT_OBJECT_0 = 0x00000000
    INFINITE = 0xFFFFFFFF

MUTEX_NAME = "Local\\LoFiHUD_SingleInstance_Mutex"
EVENT_NAME = "Local\\LoFiHUD_ActivateEvent"


class _Win32SingleInstance:
    """Ensures only a single instance of LoFi HUD runs per Windows user session."""

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


class _PosixSingleInstance:
    """Ensures only a single instance runs on macOS / POSIX using a domain socket."""

    def __init__(self, mutex_name: str = "lofi_hud", event_name: str = "lofi_hud") -> None:
        from lofi.paths import user_data_dir

        self._sock_path = os.path.join(user_data_dir(), "lofi_hud.sock")
        self._server_sock: Optional[socket.socket] = None
        self._listening = False
        self._listen_thread: Optional[threading.Thread] = None

    def acquire(self) -> bool:
        """Attempt to bind the local domain socket."""
        if os.path.exists(self._sock_path):
            try:
                test_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                test_sock.connect(self._sock_path)
                test_sock.close()
                return False  # Already running and responding
            except OSError:
                # Stale socket file from previous crash
                try:
                    os.remove(self._sock_path)
                except OSError:
                    pass

        try:
            self._server_sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self._server_sock.bind(self._sock_path)
            self._server_sock.listen(5)
            return True
        except OSError:
            return False

    def notify_running_instance(self) -> None:
        """Signal the existing instance to surface its interface."""
        if os.path.exists(self._sock_path):
            try:
                s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                s.connect(self._sock_path)
                s.sendall(b"activate\n")
                s.close()
            except OSError:
                pass

    def listen_for_activation(self, callback: Callable[[], None]) -> None:
        """Listen for incoming activation signals on the unix socket."""
        if not self._server_sock:
            return
        self._listening = True

        def _listener() -> None:
            while self._listening:
                try:
                    self._server_sock.settimeout(1.0)
                    conn, _ = self._server_sock.accept()
                    data = conn.recv(64)
                    conn.close()
                    if b"activate" in data:
                        try:
                            callback()
                        except Exception:
                            pass
                except socket.timeout:
                    continue
                except OSError:
                    break

        self._listen_thread = threading.Thread(target=_listener, daemon=True)
        self._listen_thread.start()

    def release(self) -> None:
        """Close socket and remove socket file."""
        self._listening = False
        if self._server_sock:
            try:
                self._server_sock.close()
            except OSError:
                pass
            self._server_sock = None
        if os.path.exists(self._sock_path):
            try:
                os.remove(self._sock_path)
            except OSError:
                pass


SingleInstance = _Win32SingleInstance if sys.platform == "win32" else _PosixSingleInstance
