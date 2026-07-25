from __future__ import annotations

import json
from pathlib import Path

import pytest

import core.bots as bots


def test_default_layout_is_four_exact_screen_quadrants() -> None:
    assert bots.get_screen_size() == (1920, 1080)
    assert bots.get_bot_size() == (960, 540)
    assert [bots.get_bot_region(bot_id) for bot_id in range(1, 5)] == [
        (0, 0, 960, 540),
        (960, 0, 960, 540),
        (0, 540, 960, 540),
        (960, 540, 960, 540),
    ]


@pytest.fixture
def bots_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "bots.json"
    path.write_text(
        json.dumps(
            {
                "_default": 1,
                "_screen": {"width": 1920, "height": 1080},
                "_window": {"width": 960, "height": 540},
                "1": {"offset": [0, 0]},
                "2": {"offset": [960, 0]},
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(bots, "BOTS_FILE", path)
    monkeypatch.setattr(bots, "_active_bot_id", None)
    monkeypatch.delenv("BOT_ID", raising=False)
    return path


def test_default_bot_is_selected(bots_file: Path) -> None:
    assert bots.active_bot_id() == 1
    assert bots.get_bot_offset() == (0, 0)


def test_bot_two_uses_expected_offset(bots_file: Path) -> None:
    bots.set_bot(2)

    assert bots.active_bot_id() == 2
    assert bots.get_bot_offset() == (960, 0)
    assert bots.get_bot_region() == (960, 0, 960, 540)


def test_environment_can_select_bot(
    bots_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOT_ID", "2")

    assert bots.active_bot_id() == 2


def test_unknown_bot_is_rejected(bots_file: Path) -> None:
    with pytest.raises(ValueError, match="Unknown bot ID"):
        bots.set_bot(99)


@pytest.mark.parametrize("bot_id", (2.0, 2.7, True, 0, -1))
def test_invalid_bot_ids_are_rejected(
    bots_file: Path,
    bot_id: object,
) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        bots.set_bot(bot_id)  # type: ignore[arg-type]


def test_bot_relative_point_becomes_absolute(bots_file: Path) -> None:
    assert bots.to_screen_point(100, 200, bot_id=2) == (1060, 200)


def test_bot_relative_point_must_stay_inside_window(bots_file: Path) -> None:
    with pytest.raises(ValueError, match="outside"):
        bots.to_screen_point(960, 200, bot_id=2)


def test_overlapping_bot_windows_are_rejected(
    bots_file: Path,
) -> None:
    data = json.loads(bots_file.read_text(encoding="utf-8"))
    data["2"]["offset"] = [959, 0]
    bots_file.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError, match="overlaps"):
        bots.load_bots()
