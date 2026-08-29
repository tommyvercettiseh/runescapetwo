from pathlib import Path

from tools.unified_tester.action_registry import ActionContext, get_action


ROOT = Path(__file__).resolve().parents[1]


def test_click_inventory_item_is_a_registered_image_action() -> None:
    spec = get_action("Click inventory item")
    assert spec.uses_image is True
    assert spec.uses_selection is True


def test_action_context_keeps_image_name() -> None:
    context = ActionContext(bot_id=1, image_name="Item_Axe")
    assert context.image_name == "Item_Axe"


def test_unified_tester_launches_drag_builder() -> None:
    source = (ROOT / "tools" / "unified_tester" / "scenario_editor_app.py").read_text(
        encoding="utf-8"
    )
    assert "ScenarioBuilder" in source
    assert "ScenarioCodeEditor" not in source
