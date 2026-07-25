from __future__ import annotations

import json
from pathlib import Path

import pytest

import core.bots as bots


@pytest.fixture
def bots_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    path = tmp_path / "bots.json"
    path.write_text(
        json.dumps(
            {
                "_default": 1,
                "1": {"offset": [0, 0]},
                "2": {"offset": [958, 0]},
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
    assert bots.get_bot_offset() == (958, 0)


def test_environment_can_select_bot(
    bots_file: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BOT_ID", "2")

    assert bots.active_bot_id() == 2


def test_unknown_bot_is_rejected(bots_file: Path) -> None:
    with pytest.raises(ValueError, match="Unknown bot ID"):
        bots.set_bot(99)
