from importlib import import_module
from types import ModuleType

from .profile import active_profile_name, load_profile


def __getattr__(name: str) -> ModuleType:
    if name in {"keyboard", "mouse", "mouse_actions", "vision"}:
        module = import_module(f"{__name__}.{name}")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = [
    "mouse",
    "mouse_actions",
    "keyboard",
    "vision",
    "load_profile",
    "active_profile_name",
]
