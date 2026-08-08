from dataclasses import dataclass

from tools.unified_tester.action_registry import ACTION_SPECS, action_names, get_action
from tools.unified_tester.result_utils import format_result, result_detail, result_success
from tools.unified_tester.scenario_code_editor import ScenarioCodeEditor
from tools.unified_tester.scenario_runner import BANKING_SCENARIO, STEP_HANDLERS


def test_action_registry_has_unique_names() -> None:
    names = action_names()
    assert names
    assert len(names) == len(set(names))
    assert tuple(spec.name for spec in ACTION_SPECS) == names
    assert all(get_action(name).name == name for name in names)


def test_scenario_registry_covers_every_configured_step() -> None:
    configured = {step.key for step in BANKING_SCENARIO}
    assert configured == set(STEP_HANDLERS)


def test_action_maker_uses_atomic_click_image() -> None:
    source = ScenarioCodeEditor._click_image_source(
        "click_test",
        "TestImage",
        "Bot_Area",
    )
    compile(source, "click_test.py", "exec")
    assert "mouse_actions.click_image" in source
    assert "mouse.click" not in source


@dataclass(frozen=True)
class _Result:
    success: bool
    message: str


def test_result_helpers_normalize_dataclass_results() -> None:
    result = _Result(success=True, message="done")
    assert result_success(result) is True
    assert result_detail(result) == "done"
    formatted = format_result(result)
    assert "success: True" in formatted
    assert "message: done" in formatted
