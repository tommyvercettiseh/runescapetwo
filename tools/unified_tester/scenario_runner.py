from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, Literal

from actions.bank.bank_inventory import bank_inventory
from actions.bank.close_bank import close_bank
from actions.bank.find_bank import find_bank
from actions.bank.open_bank import open_bank
from definitions.bank.is_bank_all_selected import is_bank_all_selected
from definitions.bank.is_bank_closed import is_bank_closed
from definitions.bank.is_bank_open import is_bank_open
from definitions.bank.is_bank_visible import is_bank_visible
from definitions.inventory.check_inventory import check_inventory
from definitions.inventory.get_inventory_item_slots import get_inventory_item_slots


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


@dataclass(frozen=True)
class ScenarioContext:
    bot_id: int
    image_name: str
    live: bool
    mode: StepMode
    started: float


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


def _result(
    step: ScenarioStep,
    context: ScenarioContext,
    *,
    success: bool | None,
    status: str,
    message: str,
) -> ScenarioStepResult:
    return ScenarioStepResult(
        key=step.key,
        name=step.name,
        kind=step.kind,
        mode=context.mode,
        success=success,
        status=status,
        message=message,
        elapsed_ms=(time.perf_counter() - context.started) * 1000.0,
    )


def _boolean_result(
    step: ScenarioStep,
    context: ScenarioContext,
    value: bool,
    true_message: str,
    false_message: str,
) -> ScenarioStepResult:
    return _result(
        step,
        context,
        success=value,
        status="TRUE." if value else "FALSE.",
        message=true_message if value else false_message,
    )


def _bank_visible(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    return _boolean_result(
        step,
        context,
        is_bank_visible(context.bot_id),
        "Bank visible.",
        "Bank not visible.",
    )


def _bank_open(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    return _boolean_result(
        step,
        context,
        is_bank_open(context.bot_id),
        "Bank open.",
        "Bank closed.",
    )


def _bank_all(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    return _boolean_result(
        step,
        context,
        is_bank_all_selected(context.bot_id),
        "Bank All selected.",
        "Bank All is not selected.",
    )


def _bank_closed(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    return _boolean_result(
        step,
        context,
        is_bank_closed(context.bot_id),
        "Bank closed.",
        "Bank open.",
    )


def _inventory(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    inventory = check_inventory(context.bot_id, image_name="")
    return _result(
        step,
        context,
        success=True,
        status="DONE.",
        message=(
            f"Occupied {inventory.occupied_count}/28. "
            f"Full: {'TRUE' if inventory.full else 'FALSE'}. "
            f"Empty: {'TRUE' if inventory.empty else 'FALSE'}."
        ),
    )


def _protected_image(
    step: ScenarioStep,
    context: ScenarioContext,
) -> ScenarioStepResult:
    clean_name = context.image_name.strip()
    if not clean_name:
        return _result(
            step,
            context,
            success=None,
            status="SKIPPED.",
            message="No protected image configured.",
        )

    slots = tuple(
        sorted(get_inventory_item_slots(clean_name, context.bot_id))
    )
    return _result(
        step,
        context,
        success=bool(slots),
        status="TRUE." if slots else "FALSE.",
        message=(
            f"{clean_name} slots: {', '.join(map(str, slots))}."
            if slots
            else f"{clean_name} not found."
        ),
    )


def _find_bank(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    if context.live:
        return _boolean_result(
            step,
            context,
            find_bank(context.bot_id),
            "Bank found.",
            "Bank not found.",
        )

    visible = is_bank_visible(context.bot_id)
    return _result(
        step,
        context,
        success=True if visible else None,
        status="DRY.",
        message=(
            "Bank already visible."
            if visible
            else "Dry run. Camera input not sent."
        ),
    )


def _open_bank(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    if context.live:
        return _boolean_result(
            step,
            context,
            open_bank(context.bot_id),
            "Bank opened.",
            "Bank open failed.",
        )

    already_open = is_bank_open(context.bot_id)
    visible = is_bank_visible(context.bot_id)
    ready = already_open or visible
    return _result(
        step,
        context,
        success=ready,
        status="DRY." if ready else "FALSE.",
        message=(
            "Bank already open."
            if already_open
            else "Open bank ready."
            if visible
            else "Bank not visible."
        ),
    )


def _bank_inventory(
    step: ScenarioStep,
    context: ScenarioContext,
) -> ScenarioStepResult:
    clean_name = context.image_name.strip()
    action_result = bank_inventory(
        context.bot_id,
        exclude_images=[clean_name] if clean_name else [],
        dry_run=not context.live,
    )
    status = (
        "TRUE."
        if context.live and action_result.success
        else "DRY."
        if action_result.success
        else "FALSE."
    )
    return _result(
        step,
        context,
        success=action_result.success,
        status=status,
        message=action_result.message,
    )


def _close_bank(step: ScenarioStep, context: ScenarioContext) -> ScenarioStepResult:
    if context.live:
        return _boolean_result(
            step,
            context,
            close_bank(context.bot_id),
            "Bank closed.",
            "Bank close failed.",
        )

    return _result(
        step,
        context,
        success=True,
        status="DRY.",
        message=(
            "Close bank ready."
            if is_bank_open(context.bot_id)
            else "Bank already closed."
        ),
    )


ScenarioHandler = Callable[[ScenarioStep, ScenarioContext], ScenarioStepResult]

STEP_HANDLERS: dict[str, ScenarioHandler] = {
    "bank_visible": _bank_visible,
    "bank_open": _bank_open,
    "bank_all": _bank_all,
    "bank_closed": _bank_closed,
    "inventory": _inventory,
    "protected_image": _protected_image,
    "find_bank": _find_bank,
    "open_bank": _open_bank,
    "bank_inventory": _bank_inventory,
    "close_bank": _close_bank,
}


def execute_scenario_step(
    step: ScenarioStep,
    *,
    bot_id: int = 1,
    image_name: str = "Item_Axe",
    live: bool = False,
) -> ScenarioStepResult:
    try:
        handler = STEP_HANDLERS[step.key]
    except KeyError as exc:
        raise KeyError(f"Unknown scenario step: {step.key}") from exc

    context = ScenarioContext(
        bot_id=bot_id,
        image_name=image_name,
        live=live,
        mode=step_mode(step, live),
        started=time.perf_counter(),
    )
    return handler(step, context)


__all__ = [
    "BANKING_SCENARIO",
    "STEP_HANDLERS",
    "ScenarioContext",
    "ScenarioStep",
    "ScenarioStepResult",
    "execute_scenario_step",
    "step_mode",
]
