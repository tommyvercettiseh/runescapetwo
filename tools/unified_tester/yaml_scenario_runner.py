from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from core.action_trace import trace
from core.vision.areas import get_area
from core.vision.templates import template_path
from definitions.registry import get_definition
from definitions.vision.has_image_in_area import has_image_in_area
from tools.unified_tester.action_registry import ActionContext, get_action
from tools.unified_tester.result_utils import format_result, result_success


MAX_NESTING_DEPTH = 12
MAX_EXECUTED_STEPS = 500


class ScenarioError(ValueError):
    pass


@dataclass(frozen=True)
class YamlScenarioResult:
    success: bool
    name: str
    executed_steps: int
    message: str


class _ScenarioStop(Exception):
    def __init__(self, success: bool, message: str) -> None:
        super().__init__(message)
        self.success = success
        self.message = message


def parse_scenario(text: str) -> dict[str, Any]:
    data = yaml.safe_load(text)
    if not isinstance(data, dict):
        raise ScenarioError("Scenario YAML must contain one top-level object.")
    validate_scenario(data)
    return data


def load_scenario(path: str | Path) -> dict[str, Any]:
    return parse_scenario(Path(path).read_text(encoding="utf-8"))


def validate_scenario(data: dict[str, Any]) -> None:
    name = data.get("name")
    if not isinstance(name, str) or not name.strip():
        raise ScenarioError("Scenario requires a non-empty 'name'.")

    bot_id = data.get("bot_id", 1)
    if isinstance(bot_id, bool) or not isinstance(bot_id, int) or bot_id < 1:
        raise ScenarioError("bot_id must be a positive whole number.")

    steps = data.get("steps")
    if not isinstance(steps, list):
        raise ScenarioError("Scenario requires a 'steps' list.")
    _validate_steps(steps, depth=0)


def _validate_steps(steps: list[Any], *, depth: int) -> None:
    if depth > MAX_NESTING_DEPTH:
        raise ScenarioError(f"Scenario nesting exceeds {MAX_NESTING_DEPTH} levels.")

    for index, step in enumerate(steps, start=1):
        if not isinstance(step, dict) or len(step) != 1:
            raise ScenarioError(f"Step {index} must contain exactly one operation.")

        operation, value = next(iter(step.items()))
        if operation == "action":
            _parse_action(value)
        elif operation == "if":
            _validate_if(value, depth=depth)
        elif operation == "wait":
            _parse_wait(value)
        elif operation == "stop":
            _parse_stop(value)
        else:
            raise ScenarioError(f"Unknown scenario operation: {operation}")


def _validate_if(value: Any, *, depth: int) -> None:
    if not isinstance(value, dict):
        raise ScenarioError("if must contain an object.")

    condition_keys = [key for key in ("definition", "image_exists") if key in value]
    if len(condition_keys) != 1:
        raise ScenarioError("if requires exactly one condition: definition or image_exists.")

    if condition_keys[0] == "definition":
        _parse_definition_condition(value["definition"])
    else:
        _parse_image_condition(value["image_exists"])

    for branch in ("then", "else"):
        branch_steps = value.get(branch, [])
        if not isinstance(branch_steps, list):
            raise ScenarioError(f"if.{branch} must be a list.")
        _validate_steps(branch_steps, depth=depth + 1)


def _parse_definition_condition(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise ScenarioError("definition condition must contain category and name.")
    category = value.get("category")
    name = value.get("name")
    if not isinstance(category, str) or not isinstance(name, str):
        raise ScenarioError("definition condition requires string category and name.")
    get_definition(category, name)
    return category, name


def _parse_image_condition(value: Any) -> tuple[str, str]:
    if not isinstance(value, dict):
        raise ScenarioError("image_exists must contain image and area.")
    image = value.get("image")
    area = value.get("area")
    if not isinstance(image, str) or not image.strip():
        raise ScenarioError("image_exists.image must be a non-empty string.")
    if not isinstance(area, str) or not area.strip():
        raise ScenarioError("image_exists.area must be a non-empty string.")
    template_path(image)
    get_area(area)
    return image, area


def _parse_action(value: Any) -> tuple[str, dict[str, Any]]:
    if isinstance(value, str):
        name = value
        options: dict[str, Any] = {}
    elif isinstance(value, dict):
        name = value.get("name")
        options = value.get("with", {})
        if not isinstance(name, str) or not name.strip():
            raise ScenarioError("action.name must be a non-empty string.")
        if not isinstance(options, dict):
            raise ScenarioError("action.with must be an object.")
    else:
        raise ScenarioError("action must be a name or an object with name/with.")

    get_action(name)
    allowed = {
        "protected_images",
        "optional_images",
        "pattern",
        "selection",
    }
    unknown = set(options) - allowed
    if unknown:
        raise ScenarioError(
            f"Unsupported action options for {name}: {', '.join(sorted(unknown))}"
        )

    for key in ("protected_images", "optional_images"):
        if key not in options:
            continue
        values = options[key]
        if not isinstance(values, list) or not all(isinstance(item, str) for item in values):
            raise ScenarioError(f"action.with.{key} must be a list of strings.")

    for key in ("pattern", "selection"):
        if key in options and not isinstance(options[key], str):
            raise ScenarioError(f"action.with.{key} must be a string.")

    return name, options


def _parse_wait(value: Any) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ScenarioError("wait must be a number of seconds.")
    seconds = float(value)
    if not 0.0 <= seconds <= 300.0:
        raise ScenarioError("wait must be between 0 and 300 seconds.")
    return seconds


def _parse_stop(value: Any) -> bool:
    if value == "success" or value is True:
        return True
    if value == "failure" or value is False:
        return False
    raise ScenarioError("stop must be success/failure or true/false.")


class YamlScenarioRunner:
    def __init__(self, *, bot_id: int, dry_run: bool = False) -> None:
        self.bot_id = bot_id
        self.dry_run = dry_run
        self.executed_steps = 0

    def run(self, data: dict[str, Any]) -> YamlScenarioResult:
        validate_scenario(data)
        name = str(data["name"])
        trace(f"[SCENARIO] start {name} bot={self.bot_id} dry_run={self.dry_run}")
        try:
            self._run_steps(data["steps"], depth=0)
        except _ScenarioStop as stop:
            trace(f"[SCENARIO] stop success={stop.success}: {stop.message}")
            return YamlScenarioResult(stop.success, name, self.executed_steps, stop.message)

        trace("[SCENARIO] completed")
        return YamlScenarioResult(True, name, self.executed_steps, "Scenario completed.")

    def _count_step(self) -> None:
        self.executed_steps += 1
        if self.executed_steps > MAX_EXECUTED_STEPS:
            raise ScenarioError(
                f"Scenario exceeded the {MAX_EXECUTED_STEPS}-step execution limit."
            )

    def _run_steps(self, steps: list[Any], *, depth: int) -> None:
        if depth > MAX_NESTING_DEPTH:
            raise ScenarioError(f"Scenario nesting exceeds {MAX_NESTING_DEPTH} levels.")

        for step in steps:
            self._count_step()
            operation, value = next(iter(step.items()))

            if operation == "if":
                self._run_if(value, depth=depth)
            elif operation == "action":
                self._run_action(value)
            elif operation == "wait":
                seconds = _parse_wait(value)
                trace(f"[WAIT] {seconds:g}s")
                if not self.dry_run:
                    time.sleep(seconds)
            elif operation == "stop":
                success = _parse_stop(value)
                raise _ScenarioStop(success, "Explicit stop.")

    def _run_if(self, value: dict[str, Any], *, depth: int) -> None:
        if "definition" in value:
            category, name = _parse_definition_condition(value["definition"])
            result = bool(get_definition(category, name).function(self.bot_id))
            trace(f"[IF] definition {category} / {name} = {result}")
        else:
            image, area = _parse_image_condition(value["image_exists"])
            result = has_image_in_area(image, area, self.bot_id)
            trace(f"[IF] image_exists image={image} area={area} = {result}")

        branch = "then" if result else "else"
        trace(f"[BRANCH] {branch}")
        self._run_steps(value.get(branch, []), depth=depth + 1)

    def _run_action(self, value: Any) -> None:
        name, options = _parse_action(value)
        trace(f"[ACTION] {name}")
        context = ActionContext(
            bot_id=self.bot_id,
            protected_images=tuple(options.get("protected_images", ())),
            optional_images=tuple(options.get("optional_images", ())),
            pattern=str(options.get("pattern", "random_pattern")),
            selection=str(options.get("selection", "nearest")),
            dry_run=self.dry_run,
        )
        result = get_action(name).execute(context)
        compact_result = format_result(result).replace("\n", " | ")
        trace(f"[ACTION RESULT] {name}: {compact_result}")

        success = result_success(result)
        if not self.dry_run and success is False:
            raise _ScenarioStop(False, f"Action failed: {name}")


def run_scenario_data(
    data: dict[str, Any],
    *,
    bot_id: int | None = None,
    dry_run: bool = False,
) -> YamlScenarioResult:
    validate_scenario(data)
    resolved_bot_id = int(data.get("bot_id", 1) if bot_id is None else bot_id)
    if resolved_bot_id < 1:
        raise ScenarioError("bot_id must be positive.")
    return YamlScenarioRunner(bot_id=resolved_bot_id, dry_run=dry_run).run(data)


__all__ = [
    "ScenarioError",
    "YamlScenarioResult",
    "YamlScenarioRunner",
    "load_scenario",
    "parse_scenario",
    "run_scenario_data",
    "validate_scenario",
]
