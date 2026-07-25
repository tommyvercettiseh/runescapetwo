from __future__ import annotations

from copy import deepcopy
import json
from pathlib import Path

import pytest

import core.profile as profile


@pytest.fixture
def valid_profile() -> dict:
    default_path = Path(__file__).resolve().parents[1] / "profiles" / "default.json"
    return json.loads(default_path.read_text(encoding="utf-8"))


def test_default_profile_is_valid(valid_profile: dict) -> None:
    profile.validate_profile(valid_profile)


@pytest.mark.parametrize(
    ("section", "key"),
    (
        ("mouse", "duration_min_s"),
        ("mouse", "pre_click_min_s"),
        ("keyboard", "type_delay_min_s"),
        ("vision", "timeout_s"),
    ),
)
def test_negative_timings_are_rejected(
    valid_profile: dict,
    section: str,
    key: str,
) -> None:
    invalid = deepcopy(valid_profile)
    invalid[section][key] = -0.01

    with pytest.raises(ValueError, match="cannot be negative"):
        profile.validate_profile(invalid)


def test_minimum_above_maximum_is_rejected(valid_profile: dict) -> None:
    invalid = deepcopy(valid_profile)
    invalid["mouse"]["duration_min_s"] = 2.0
    invalid["mouse"]["duration_max_s"] = 1.0

    with pytest.raises(ValueError, match="cannot be greater"):
        profile.validate_profile(invalid)


def test_unknown_movement_is_rejected(valid_profile: dict) -> None:
    invalid = deepcopy(valid_profile)
    invalid["mouse"]["movement_method"] = "missing"

    with pytest.raises(ValueError, match="Unknown movement method"):
        profile.validate_profile(invalid)


def test_load_profile_activates_only_valid_data(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    valid_profile: dict,
) -> None:
    monkeypatch.setattr(profile, "PROFILES_DIR", tmp_path)
    (tmp_path / "personal.json").write_text(
        json.dumps(valid_profile),
        encoding="utf-8",
    )

    loaded = profile.load_profile("personal")

    assert loaded == valid_profile
    assert profile.active_profile_name() == "personal"


def test_profile_name_cannot_escape_profile_directory() -> None:
    with pytest.raises(ValueError, match="plain file name"):
        profile.load_profile("../personal")
