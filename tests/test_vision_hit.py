from __future__ import annotations

import pytest

from core.vision.models import Hit


@pytest.fixture
def hit() -> Hit:
    return Hit(
        x=100,
        y=200,
        width=20,
        height=10,
        shape_score=95.0,
        color_score=80.0,
        method="TM_CCOEFF_NORMED",
    )


def test_hit_center_and_topleft_anchors(hit: Hit) -> None:
    assert hit.point("center", padding=4) == (110, 205)
    assert hit.point("topleft", padding=4) == (100, 200)


def test_hit_random_point_respects_padding(
    hit: Hit,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    values: list[tuple[int, int]] = []

    def fake_randint(start: int, end: int) -> int:
        values.append((start, end))
        return start

    monkeypatch.setattr("core.vision.models.random.randint", fake_randint)

    assert hit.point("random", padding=3) == (103, 203)
    assert values == [(103, 116), (203, 206)]


def test_hit_uses_center_when_padding_is_too_large(hit: Hit) -> None:
    assert hit.point("random", padding=20) == hit.center


def test_hit_rejects_unknown_anchor_and_negative_padding(hit: Hit) -> None:
    with pytest.raises(ValueError, match="anchor"):
        hit.point("bottom")
    with pytest.raises(ValueError, match="padding"):
        hit.random_point(-1)
