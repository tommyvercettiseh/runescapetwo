from __future__ import annotations

from dataclasses import dataclass
import random


@dataclass(frozen=True)
class TemplateSettings:
    method: str
    min_shape: float
    min_color: float
    area: str | None = None


@dataclass(frozen=True)
class MatchResult:
    x: int
    y: int
    width: int
    height: int
    shape_score: float
    color_score: float
    method: str

    @property
    def center(self) -> tuple[int, int]:
        return self.x + self.width // 2, self.y + self.height // 2


@dataclass(frozen=True)
class Hit(MatchResult):
    def random_point(self, padding: int = 0) -> tuple[int, int]:
        padding = max(0, int(padding))
        left = self.x + padding
        top = self.y + padding
        right = self.x + self.width - padding - 1
        bottom = self.y + self.height - padding - 1

        if right < left or bottom < top:
            return self.center

        return random.randint(left, right), random.randint(top, bottom)


@dataclass(frozen=True)
class ColourBlob:
    """One connected colour region in absolute screen coordinates."""

    x: int
    y: int
    width: int
    height: int
    area_px: float
    centroid_x: int
    centroid_y: int

    @property
    def center(self) -> tuple[int, int]:
        return self.centroid_x, self.centroid_y

    def random_point(self, padding: int = 0) -> tuple[int, int]:
        padding = max(0, int(padding))
        left = self.x + padding
        top = self.y + padding
        right = self.x + self.width - padding - 1
        bottom = self.y + self.height - padding - 1
        if right < left or bottom < top:
            return self.center
        return random.randint(left, right), random.randint(top, bottom)
