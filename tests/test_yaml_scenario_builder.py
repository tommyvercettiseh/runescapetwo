from __future__ import annotations

from tools.unified_tester.yaml_scenario_builder import (
    default_scenario_data,
    dump_scenario_yaml,
)
from tools.unified_tester.yaml_scenario_runner import parse_scenario


def test_empty_builder_scenario_round_trips_through_runner() -> None:
    data = default_scenario_data()
    parsed = parse_scenario(dump_scenario_yaml(data))

    assert parsed == data


def test_card_style_flow_round_trips_through_runner(monkeypatch) -> None:
    from tools.unified_tester import yaml_scenario_runner as runner

    class Definition:
        function = staticmethod(lambda _bot_id: True)

    monkeypatch.setattr(runner, "get_definition", lambda _category, _name: Definition())
    monkeypatch.setattr(runner, "get_action", lambda _name: object())

    data = {
        "name": "Card flow",
        "bot_id": 1,
        "steps": [
            {
                "if": {
                    "definition": {
                        "category": "Login",
                        "name": "Logged in.",
                    },
                    "then": [{"action": "Open bank"}],
                    "else": [{"action": "Login"}],
                }
            },
            {"wait": 0.5},
            {"stop": "success"},
        ],
    }

    parsed = parse_scenario(dump_scenario_yaml(data))
    assert parsed == data
