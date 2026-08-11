from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, runtime_checkable

import numpy as np


Region = tuple[int, int, int, int]
Bounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class PreviewMode:
    """One page-supported desktop preview mode."""

    key: str
    label: str
    description: str


@dataclass(frozen=True)
class PreviewBox:
    """One annotation drawn over the real game window, local to the region."""

    bounds: Bounds
    colour: str
    width: int = 2
    label: str = ""


@dataclass(frozen=True)
class PreviewSnapshot:
    """Desktop preview payload for one absolute game region.

    ``frame`` is optional. Colour and sensor previews normally provide a full
    processed RGB frame. Template matching intentionally omits the frame and
    provides only annotation boxes, so the real RuneLite pixels remain visible
    underneath the overlay.
    """

    region: Region
    frame: np.ndarray | None = None
    boxes: tuple[PreviewBox, ...] = ()


@runtime_checkable
class DesktopPreviewPage(Protocol):
    """Explicit contract implemented by pages that support game-window preview."""

    def desktop_preview_modes(self) -> tuple[PreviewMode, ...]: ...

    def desktop_preview_default_mode(self) -> str: ...

    def desktop_preview_snapshot(self, mode_key: str) -> PreviewSnapshot | None: ...

    def set_desktop_preview_compact(self, enabled: bool) -> None: ...


__all__ = [
    "Bounds",
    "DesktopPreviewPage",
    "PreviewBox",
    "PreviewMode",
    "PreviewSnapshot",
    "Region",
]
