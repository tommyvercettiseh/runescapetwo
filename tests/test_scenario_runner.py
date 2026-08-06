from __future__ import annotations

from types import SimpleNamespace

import tools.unified_tester.scenario_runner as scenario_runner


def step(key: str):
    return next(item for item in scenario_runner.BANKING_SCENARIO if item.key == key)


def test_sensors_always_use_read_mode() -> None:
    sensor = step("bank_open")

    assert scenario_runner.step_mode(sensor, live=False) == "read"
    assert scenario_runner.step_mode(sensor, live=True) == "read"


def test_actions_default_to_dry_and_can_be_live() -> None:
    action = step("open_bank")

    assert scenario_runner.step_mode(action, live=False) == "dry"
    assert scenario_runner.step_mode(action, live=True) == "live"


def test_dry_find_bank_never_calls_action(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        scenario_runner,
        "is_bank_visible",
        lambda _bot_id: False,
    )
    monkeypatch.setattr(
        scenario_runner,
        "find_bank",
        lambda _bot_id: calls.append("find") or True,
    )

    result = scenario_runner.execute_scenario_step(
        step("find_bank"),
        live=False,
    )

    assert result.mode == "dry"
    assert result.status == "DRY."
    assert result.success is None
    assert calls == []


def test_live_find_bank_calls_action(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        scenario_runner,
        "find_bank",
        lambda bot_id: calls.append(bot_id) or True,
    )

    result = scenario_runner.execute_scenario_step(
        step("find_bank"),
        bot_id=3,
        live=True,
    )

    assert result.mode == "live"
    assert result.status == "TRUE."
    assert result.success is True
    assert calls == [3]


def test_bank_inventory_dry_run_passes_dry_flag(monkeypatch) -> None:
    calls = []

    def fake_bank_inventory(bot_id, **settings):
        calls.append((bot_id, settings))
        return SimpleNamespace(success=True, message="Dry run complete.")

    monkeypatch.setattr(
        scenario_runner,
        "bank_inventory",
        fake_bank_inventory,
    )

    result = scenario_runner.execute_scenario_step(
        step("bank_inventory"),
        bot_id=2,
        image_name="Item_Axe",
        live=False,
    )

    assert result.status == "DRY."
    assert result.success is True
    assert calls == [
        (
            2,
            {
                "exclude_images": ["Item_Axe"],
                "dry_run": True,
            },
        )
    ]


def test_bank_inventory_live_disables_dry_run(monkeypatch) -> None:
    calls = []

    def fake_bank_inventory(bot_id, **settings):
        calls.append((bot_id, settings))
        return SimpleNamespace(success=True, message="Banking complete.")

    monkeypatch.setattr(
        scenario_runner,
        "bank_inventory",
        fake_bank_inventory,
    )

    result = scenario_runner.execute_scenario_step(
        step("bank_inventory"),
        bot_id=4,
        image_name="",
        live=True,
    )

    assert result.status == "TRUE."
    assert result.success is True
    assert calls == [
        (
            4,
            {
                "exclude_images": [],
                "dry_run": False,
            },
        )
    ]


def test_protected_image_can_be_skipped(monkeypatch) -> None:
    calls = []
    monkeypatch.setattr(
        scenario_runner,
        "get_inventory_item_slots",
        lambda *args: calls.append(args) or {1},
    )

    result = scenario_runner.execute_scenario_step(
        step("protected_image"),
        image_name="   ",
    )

    assert result.status == "SKIPPED."
    assert result.success is None
    assert calls == []


def test_protected_image_reports_slots(monkeypatch) -> None:
    monkeypatch.setattr(
        scenario_runner,
        "get_inventory_item_slots",
        lambda image_name, bot_id: {7, 2},
    )

    result = scenario_runner.execute_scenario_step(
        step("protected_image"),
        bot_id=2,
        image_name="Item_Axe",
    )

    assert result.status == "TRUE."
    assert result.success is True
    assert result.message == "Item_Axe slots: 2, 7."
