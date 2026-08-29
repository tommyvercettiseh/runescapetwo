from pathlib import Path

from tools.unified_tester.action_registry import ActionContext, get_action


ROOT = Path(__file__).resolve().parents[1]


def test_click_inventory_item_is_a_registered_image_action() -> None:
    spec = get_action("Click inventory item")
    assert spec.uses_image is True
    assert spec.uses_selection is True


def test_click_image_is_registered_with_image_and_area() -> None:
    spec = get_action("Click image")
    assert spec.uses_image is True
    assert spec.uses_area is True


def test_action_context_keeps_image_and_area() -> None:
    context = ActionContext(
        bot_id=1,
        image_name="BankDeposit",
        area_name="Bank_Area",
    )
    assert context.image_name == "BankDeposit"
    assert context.area_name == "Bank_Area"


def test_click_image_dry_run_reads_selected_area(monkeypatch) -> None:
    seen: dict[str, object] = {}

    def fake_find_image(image_name: str, *, area: str, bot_id: int):
        seen.update(image=image_name, area=area, bot_id=bot_id)
        return object()

    monkeypatch.setattr(
        "tools.unified_tester.action_registry.find_image",
        fake_find_image,
    )

    result = get_action("Click image").execute(
        ActionContext(
            bot_id=2,
            image_name="BankDeposit",
            area_name="Bank_Area",
            dry_run=True,
        )
    )

    assert result["success"] is True
    assert seen == {
        "image": "BankDeposit",
        "area": "Bank_Area",
        "bot_id": 2,
    }


def test_unified_tester_launches_dynamic_drag_builder() -> None:
    source = (ROOT / "tools" / "unified_tester" / "scenario_editor_app.py").read_text(
        encoding="utf-8"
    )
    assert "DynamicScenarioBuilder" in source
    assert "ScenarioCodeEditor" not in source
