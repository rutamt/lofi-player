__version__ = "1.0.1"
__all__ = ["App", "__version__"]


def __getattr__(name: str):
    if name == "App":
        from lofi.app import App

        return App
    raise AttributeError("module {!r} has no attribute {!r}".format(__name__, name))
