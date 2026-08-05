from __future__ import annotations

import json
from pathlib import Path

import pytest

from core import mouse_engine


class FakeProvider:
    def manifest(self):
        return {"api_version": 1, "name": "fake", "version": "1.0"}

    def create_plan(self, *args, **kwargs):
        return {"args": args, "kwargs": kwargs}


class FakeEntryPoint:
    name = "fake"

    def load(self):
        return FakeProvider


def test_settings_roundtrip_and_profile_expansion(tmp_path, monkeypatch):
    profile = tmp_path / "master_profile.json"
    profile.write_text("{}", encoding="utf-8")
    config = tmp_path / "mouse_engine.json"
    monkeypatch.setenv("TEST_MOUSE_PROFILE", str(profile))

    saved = mouse_engine.save_settings(
        {
            "enabled": True,
            "provider": "fake",
            "profile_path": "$TEST_MOUSE_PROFILE",
        },
        config,
    )
    loaded = mouse_engine.load_settings(config)

    assert saved == loaded
    assert json.loads(config.read_text(encoding="utf-8"))["provider"] == "fake"
    assert mouse_engine.configured_profile_path(loaded) == profile


def test_provider_is_discovered_through_stable_entry_point(monkeypatch):
    mouse_engine.reset_provider_cache()
    monkeypatch.setattr(mouse_engine, "entry_points", lambda group: [FakeEntryPoint()])

    provider = mouse_engine.get_provider({"enabled": True, "provider": "fake"})

    assert provider.manifest()["api_version"] == 1


def test_provider_api_mismatch_is_rejected(monkeypatch):
    class WrongProvider(FakeProvider):
        def manifest(self):
            return {"api_version": 99}

    class WrongEntryPoint(FakeEntryPoint):
        def load(self):
            return WrongProvider

    mouse_engine.reset_provider_cache()
    monkeypatch.setattr(mouse_engine, "entry_points", lambda group: [WrongEntryPoint()])

    with pytest.raises(mouse_engine.MouseEngineUnavailable, match="unsupported"):
        mouse_engine.get_provider({"enabled": True, "provider": "fake"})


def test_create_plan_passes_local_profile_and_target_to_provider(tmp_path, monkeypatch):
    profile = tmp_path / "master_profile.json"
    profile.write_text('{"trial_count": 1}', encoding="utf-8")
    provider = FakeProvider()
    monkeypatch.setattr(mouse_engine, "get_provider", lambda settings: provider)
    settings = {
        "enabled": True,
        "provider": "fake",
        "profile_path": str(profile),
        "default_padding_px": 3,
    }

    result = mouse_engine.create_plan(
        (10, 20),
        {"left": 100, "top": 100, "right": 160, "bottom": 140},
        coordinate_size=(2560, 1440),
        settings=settings,
    )

    assert result["kwargs"]["profile_path"] == profile
    assert result["kwargs"]["padding_px"] == 3
    assert result["kwargs"]["coordinate_size"] == (2560, 1440)
