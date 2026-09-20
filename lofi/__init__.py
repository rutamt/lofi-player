"""LoFi HUD — background LoFi playback daemon for Windows."""

__all__ = ["App"]


def __getattr__(name: str):
    if name == "App":
        from lofi.app import App

        return App
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
