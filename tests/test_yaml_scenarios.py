from __future__ import annotations

from types import SimpleNamespace

import pytest

from tools.unified_tester import yaml_scenario_runner as scenarios


def test_example_scenario_is_valid() -> None:
    data = scenarios.load_scenario("scenarios/login_and_open_bank.yaml")
    assert data["name"] == "Login and open bank"


def test_if_else_runs_only_selected_branch(monkeypatch) -> None:
    actions: list[str] = []

    monkeypatch.setattr(
        scenarios,
        "get_definition",
        lambda _category, _name: SimpleNamespace(function=lambda _bot_id: False),
    )
    monkeypatch.setattr(
        scenarios,
        "get_action",
        lambda name: SimpleNamespace(
            execute=lambda _context: actions.append(name) or True,
        ),
    )

    data = {
        "name": "Branch test",
        "steps": [
            {
                "if": {
                    "definition": {"category": "Any", "name": "Any"},
                    "then": [{"action": "Then"}],
                    "else": [{"action": "Else"}],
                }
            }
        ],
    }

    result = scenarios.run_scenario_data(data, bot_id=2)
    assert result.success
    assert actions == ["Else"]


def test_failed_action_stops_scenario(monkeypatch) -> None:
    actions: list[str] = []

    monkeypatch.setattr(
        scenarios,
        "get_action",
        lambda name: SimpleNamespace(
            execute=lambda _context: actions.append(name) or (name != "Fail"),
        ),
    )

    data = {
        "name": "Failure test",
        "steps": [
            {"action": "Fail"},
            {"action": "Never"},
        ],
    }

    result = scenarios.run_scenario_data(data)
    assert not result.success
    assert actions == ["Fail"]


def test_image_exists_condition_uses_generic_definition(monkeypatch) -> None:
    monkeypatch.setattr(scenarios, "template_path", lambda image: image)
    monkeypatch.setattr(scenarios, "get_area", lambda area: area)
    monkeypatch.setattr(
        scenarios,
        "has_image_in_area",
        lambda image, area, bot_id: (image, area, bot_id)
        == ("Item_Test", "Inventory_Area", 3),
    )

    data = {
        "name": "Image test",
        "steps": [
            {
                "if": {
                    "image_exists": {
                        "image": "Item_Test",
                        "area": "Inventory_Area",
                    },
                    "then": [{"stop": "success"}],
                    "else": [{"stop": "failure"}],
                }
            }
        ],
    }

    result = scenarios.run_scenario_data(data, bot_id=3)
    assert result.success


def test_unknown_operation_is_rejected() -> None:
    with pytest.raises(scenarios.ScenarioError, match="Unknown scenario operation"):
        scenarios.validate_scenario(
            {
                "name": "Invalid",
                "steps": [{"python": "do_anything"}],
            }
        )
