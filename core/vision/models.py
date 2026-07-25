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
    def point(
        self,
        anchor: str = "random",
        padding: int = 0,
    ) -> tuple[int, int]:
        if anchor == "center":
            return self.center
        if anchor == "topleft":
            return self.x, self.y
        if anchor == "random":
            return self.random_point(padding)
        raise ValueError(
            "anchor must be 'random', 'center', or 'topleft'"
        )

    def random_point(self, padding: int = 0) -> tuple[int, int]:
        padding = int(padding)
        if padding < 0:
            raise ValueError("padding cannot be negative")
        left = self.x + padding
        top = self.y + padding
        right = self.x + self.width - padding - 1
        bottom = self.y + self.height - padding - 1

        if right < left or bottom < top:
            return self.center

        return random.randint(left, right), random.randint(top, bottom)
