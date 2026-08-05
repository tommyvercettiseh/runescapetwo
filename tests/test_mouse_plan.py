from __future__ import annotations

import pytest

from core.mouse_plan import MousePlanValidationError, validate_mouse_plan


def valid_plan() -> dict:
    return {
        "events": [
            {"type": "move", "t_ms": 0, "x": 10, "y": 20},
            {"type": "move", "t_ms": 100, "x": 150, "y": 120},
            {"type": "button_down", "t_ms": 150, "x": 150, "y": 120},
            {"type": "button_up", "t_ms": 220, "x": 150, "y": 120},
        ]
    }


def validate(plan: object, *, require_click: bool = True) -> None:
    validate_mouse_plan(
        plan,
        target={"left": 100, "top": 80, "right": 200, "bottom": 160},
        screen_size=(1920, 1080),
        require_click=require_click,
    )


def test_valid_plan_is_accepted() -> None:
    plan = valid_plan()
    assert validate_mouse_plan(
        plan,
        target={"left": 100, "top": 80, "right": 200, "bottom": 160},
        screen_size=(1920, 1080),
        require_click=True,
    ) is plan


@pytest.mark.parametrize(
    ("change", "message"),
    [
        (lambda plan: plan["events"][1].update(x=2000), "outside the screen"),
        (lambda plan: plan["events"][1].update(t_ms=-1), "must not go backwards"),
        (lambda plan: plan["events"][1].update(type="drag"), "unsupported type"),
        (lambda plan: plan["events"][2].update(x=50), "outside the safe target"),
    ],
)
def test_unsafe_provider_output_is_rejected(change, message: str) -> None:
    plan = valid_plan()
    change(plan)
    with pytest.raises(MousePlanValidationError, match=message):
        validate(plan)


def test_click_action_requires_a_complete_click() -> None:
    plan = valid_plan()
    plan["events"] = plan["events"][:2]
    with pytest.raises(MousePlanValidationError, match="requires button events"):
        validate(plan)


def test_pressed_button_must_always_be_released() -> None:
    plan = valid_plan()
    plan["events"].pop()
    with pytest.raises(MousePlanValidationError, match="leaves the button pressed"):
        validate(plan)


def test_provider_may_not_click_twice_or_drag_outside_target() -> None:
    twice = valid_plan()
    twice["events"].extend(
        [
            {"type": "button_down", "t_ms": 300, "x": 150, "y": 120},
            {"type": "button_up", "t_ms": 350, "x": 150, "y": 120},
        ]
    )
    with pytest.raises(MousePlanValidationError, match="only one click"):
        validate(twice)

    drag = valid_plan()
    drag["events"].insert(
        3,
        {"type": "move", "t_ms": 180, "x": 50, "y": 50},
    )
    with pytest.raises(MousePlanValidationError, match="while pressed"):
        validate(drag)


def test_rectangle_padding_is_part_of_the_safe_click_zone() -> None:
    plan = valid_plan()
    plan["events"][2].update(x=105)
    with pytest.raises(MousePlanValidationError, match="safe target bounds"):
        validate_mouse_plan(
            plan,
            target={"left": 100, "top": 80, "right": 200, "bottom": 160},
            screen_size=(1920, 1080),
            require_click=True,
            target_padding=10,
        )
