from __future__ import annotations

from dataclasses import dataclass
import math
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
    area_px: int
    centroid_x: int
    centroid_y: int
    safe_x: int | None = None
    safe_y: int | None = None
    safe_radius: float = 0.0

    @property
    def center(self) -> tuple[int, int]:
        return self.centroid_x, self.centroid_y

    @property
    def safe_point(self) -> tuple[int, int]:
        return (
            self.centroid_x if self.safe_x is None else self.safe_x,
            self.centroid_y if self.safe_y is None else self.safe_y,
        )

    def random_point(self, padding: int = 0) -> tuple[int, int]:
        """Return a point inside the blob, away from the nearest edge."""
        available_radius = max(0.0, float(self.safe_radius) - max(0, int(padding)))
        if available_radius < 1.0:
            return self.safe_point

        angle = random.random() * math.tau
        radius = math.sqrt(random.random()) * available_radius
        x = int(round(self.safe_point[0] + math.cos(angle) * radius))
        y = int(round(self.safe_point[1] + math.sin(angle) * radius))
        return (
            min(max(x, self.x), self.x + self.width - 1),
            min(max(y, self.y), self.y + self.height - 1),
        )
