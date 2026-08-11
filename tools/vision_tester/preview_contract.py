from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


Region = tuple[int, int, int, int]


@dataclass(frozen=True)
class PreviewMode:
    """One page-supported desktop preview mode."""

    key: str
    label: str
    description: str


@dataclass(frozen=True)
class PreviewSnapshot:
    """Frame + absolute desktop region to render on the game window."""

    frame: np.ndarray
    region: Region


@runtime_checkable
class DesktopPreviewPage(Protocol):
    """Explicit contract implemented by pages that support game-window preview."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]: ...

    def desktop_preview_default_mode(self) -> str: ...

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None: ...

    def set_desktop_preview_compact(self, enabled: bool) -> None: ...


__all__ = [
    "DesktopPreviewPage",
    "PreviewMode",
    "PreviewSnapshot",
    "Region",
]
