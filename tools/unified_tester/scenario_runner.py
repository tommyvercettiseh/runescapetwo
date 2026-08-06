from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Literal

from actions.bank.bank_inventory import bank_inventory
from actions.bank.close_bank import close_bank
from actions.bank.find_bank import find_bank
from actions.bank.open_bank import open_bank
from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots
from tools.unified_tester.inventory_checker import check_inventory


StepKind = Literal["sensor", "check", "action"]
StepMode = Literal["read", "dry", "live"]


@dataclass(frozen=True)
class ScenarioStep:
    key: str
    name: str
    kind: StepKind
    live_supported: bool = False


@dataclass(frozen=True)
class ScenarioStepResult:
    key: str
    name: str
    kind: StepKind
    mode: StepMode
    success: bool | None
    status: str
    message: str
    elapsed_ms: float

    def blocks_chain(self) -> bool:
        return self.success is False


BANKING_SCENARIO: tuple[ScenarioStep, ...] = (
    ScenarioStep("find_bank", "Find bank.", "action", live_supported=True),
    ScenarioStep("bank_visible", "Bank visible.", "sensor"),
    ScenarioStep("open_bank", "Open bank.", "action", live_supported=True),
    ScenarioStep("bank_open", "Bank open.", "sensor"),
    ScenarioStep("bank_all", "Bank All selected.", "sensor"),
    ScenarioStep("inventory", "Inventory checked.", "check"),
    ScenarioStep("protected_image", "Protected image found.", "check"),
    ScenarioStep("bank_inventory", "Bank inventory.", "action", live_supported=True),
    ScenarioStep("close_bank", "Close bank.", "action", live_supported=True),
    ScenarioStep("bank_closed", "Bank closed.", "sensor"),
)


def step_mode(step: ScenarioStep, live: bool) -> StepMode:
    if step.kind != "action":
        return "read"
    return "live" if live else "dry"


def _boolean_result(
    step: ScenarioStep,
    mode: StepMode,
    value: bool,
    true_message: str,
    false_message: str,
    started: float,
) -> ScenarioStepResult:
    return ScenarioStepResult(
        key=step.key,
        name=step.name,
        kind=step.kind,
        mode=mode,
        success=value,
        status="TRUE." if value else "FALSE.",
        message=true_message if value else false_message,
        elapsed_ms=(time.perf_counter() - started) * 1000.0,
    )


def execute_scenario_step(
    step: ScenarioStep,
    *,
    bot_id: int = 1,
    image_name: str = "Item_Axe",
    live: bool = False,
) -> ScenarioStepResult:
    mode = step_mode(step, live)
    started = time.perf_counter()

    if step.key == "bank_visible":
        return _boolean_result(
            step,
            mode,
            is_bank_visible(bot_id),
            "Bank visible.",
            "Bank not visible.",
            started,
        )

    if step.key == "bank_open":
        return _boolean_result(
            step,
            mode,
            is_bank_open(bot_id),
            "Bank open.",
            "Bank closed.",
            started,
        )

    if step.key == "bank_all":
        return _boolean_result(
            step,
            mode,
            is_bank_all_selected(bot_id),
            "Bank All selected.",
            "Bank All is not selected.",
            started,
        )

    if step.key == "bank_closed":
        return _boolean_result(
            step,
            mode,
            is_bank_closed(bot_id),
            "Bank closed.",
            "Bank open.",
            started,
        )

    if step.key == "inventory":
        inventory = check_inventory(bot_id, image_name="")
        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=True,
            status="DONE.",
            message=(
                f"Occupied {inventory.occupied_count}/28. "
                f"Full: {'TRUE' if inventory.full else 'FALSE'}. "
                f"Empty: {'TRUE' if inventory.empty else 'FALSE'}."
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    if step.key == "protected_image":
        clean_name = image_name.strip()
        if not clean_name:
            return ScenarioStepResult(
                key=step.key,
                name=step.name,
                kind=step.kind,
                mode=mode,
                success=None,
                status="SKIPPED.",
                message="No protected image configured.",
                elapsed_ms=(time.perf_counter() - started) * 1000.0,
            )

        slots = tuple(sorted(get_inventory_item_slots(clean_name, bot_id)))
        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=bool(slots),
            status="TRUE." if slots else "FALSE.",
            message=(
                f"{clean_name} slots: {', '.join(map(str, slots))}."
                if slots
                else f"{clean_name} not found."
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    if step.key == "find_bank":
        if live:
            return _boolean_result(
                step,
                mode,
                find_bank(bot_id),
                "Bank found.",
                "Bank not found.",
                started,
            )

        visible = is_bank_visible(bot_id)
        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=True if visible else None,
            status="DRY.",
            message=(
                "Bank already visible."
                if visible
                else "Dry run. Camera input not sent."
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    if step.key == "open_bank":
        if live:
            return _boolean_result(
                step,
                mode,
                open_bank(bot_id),
                "Bank opened.",
                "Bank open failed.",
                started,
            )

        already_open = is_bank_open(bot_id)
        visible = is_bank_visible(bot_id)
        ready = already_open or visible
        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=ready,
            status="DRY." if ready else "FALSE.",
            message=(
                "Bank already open."
                if already_open
                else "Open bank ready."
                if visible
                else "Bank not visible."
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    if step.key == "bank_inventory":
        clean_name = image_name.strip()
        result = bank_inventory(
            bot_id,
            exclude_images=[clean_name] if clean_name else [],
            dry_run=not live,
        )
        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=result.success,
            status=(
                "TRUE."
                if live and result.success
                else "DRY."
                if result.success
                else "FALSE."
            ),
            message=result.message,
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    if step.key == "close_bank":
        if live:
            return _boolean_result(
                step,
                mode,
                close_bank(bot_id),
                "Bank closed.",
                "Bank close failed.",
                started,
            )

        return ScenarioStepResult(
            key=step.key,
            name=step.name,
            kind=step.kind,
            mode=mode,
            success=True,
            status="DRY.",
            message=(
                "Close bank ready."
                if is_bank_open(bot_id)
                else "Bank already closed."
            ),
            elapsed_ms=(time.perf_counter() - started) * 1000.0,
        )

    raise KeyError(f"Unknown scenario step: {step.key}")
