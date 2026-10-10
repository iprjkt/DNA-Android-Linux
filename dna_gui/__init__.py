"""DNA-Linux Graphical User Interface (GUI) package."""

__all__ = ["start_gui", "MainWindow"]

def __getattr__(name: str):
    if name in ("start_gui", "MainWindow"):
        from dna_gui.app import MainWindow, start_gui
        return locals()[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
