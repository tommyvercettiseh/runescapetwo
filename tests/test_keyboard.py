from __future__ import annotations

from types import SimpleNamespace

import pytest

import core.keyboard as keyboard


@pytest.fixture
def actions(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, str]]:
    recorded: list[tuple[str, str]] = []
    controller = SimpleNamespace(
        press=lambda key: recorded.append(("press", key)),
        release=lambda key: recorded.append(("release", key)),
        type=lambda key: recorded.append(("type", key)),
    )
    monkeypatch.setattr(keyboard, "_get_controller", lambda: controller)
    monkeypatch.setattr(keyboard, "_resolve", lambda key: key)
    monkeypatch.setattr(keyboard.time, "sleep", lambda _seconds: None)
    return recorded


def test_press_always_releases_key(actions: list[tuple[str, str]]) -> None:
    keyboard.press("space")

    assert actions == [("press", "space"), ("release", "space")]


def test_hotkey_releases_in_reverse_order(
    actions: list[tuple[str, str]],
) -> None:
    keyboard.hotkey("ctrl", "a")

    assert actions == [
        ("press", "ctrl"),
        ("press", "a"),
        ("release", "a"),
        ("release", "ctrl"),
    ]


@pytest.mark.parametrize("duration", (True, -1, float("nan"), "1"))
def test_hold_rejects_invalid_duration(
    actions: list[tuple[str, str]],
    duration: object,
) -> None:
    with pytest.raises(ValueError, match="finite non-negative"):
        keyboard.hold("shift", duration)  # type: ignore[arg-type]
