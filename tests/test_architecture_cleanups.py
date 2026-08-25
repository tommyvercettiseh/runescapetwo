from dataclasses import dataclass
from pathlib import Path

from definitions.inventory.constants import INVENTORY_COLUMNS, TOTAL_SLOTS
from definitions.inventory.exclusions import resolve_inventory_exclusions
from tools.unified_tester.action_registry import ACTION_SPECS, action_names, get_action
from tools.unified_tester.result_utils import format_result, result_detail, result_success
from tools.unified_tester.scenario_code_editor import ScenarioCodeEditor
from tools.unified_tester.scenario_runner import BANKING_SCENARIO, STEP_HANDLERS
from tools.vision_tester.colour_base import ColourBasePage
from tools.vision_tester.colour_browser import BrowserToleranceColourPage
from tools.vision_tester.colour_page import ColourPage
from tools.vision_tester.preset_ui import PresetColourPage
from tools.vision_tester.sensor_boolean_badge import EnhancedSensorPage
from tools.vision_tester.sensor_page import SensorPage
from tools.vision_tester.template_page import TemplatePage
from tools.vision_tester.template_plus import SearchableTemplatePage
from tools.vision_tester.unified_plus import ToleranceColourPage


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


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


def test_inventory_layout_has_one_canonical_shape() -> None:
    assert TOTAL_SLOTS == 28
    assert INVENTORY_COLUMNS == 4
    assert TOTAL_SLOTS % INVENTORY_COLUMNS == 0


def test_inventory_exclusions_share_required_and_optional_rules(monkeypatch) -> None:
    slots = {
        "Required": {3, 4},
        "Optional": {8},
        "Missing": set(),
    }
    monkeypatch.setattr(
        "definitions.inventory.exclusions.get_inventory_item_slots",
        lambda name, _bot_id: slots[name],
    )

    excluded, missing = resolve_inventory_exclusions(
        bot_id=1,
        explicit_slots={1},
        protected_images=["Required", "Missing"],
        optional_images=["Optional"],
    )
    assert excluded == {1, 3, 4, 8}
    assert missing == ("Missing",)


def test_colour_page_has_one_clear_behaviour_base() -> None:
    assert ColourPage.__bases__ == (BrowserToleranceColourPage,)
    assert BrowserToleranceColourPage.__bases__ == (ColourBasePage,)
    assert ColourPage.__mro__[:3] == (
        ColourPage,
        BrowserToleranceColourPage,
        ColourBasePage,
    )

    # Historical import names remain adapters, not extra inheritance layers.
    assert PresetColourPage is BrowserToleranceColourPage
    assert ToleranceColourPage is BrowserToleranceColourPage


def test_colour_workspace_does_not_embed_replay_or_stoplights() -> None:
    source = _source("tools/vision_tester/colour_page.py")
    assert "StoplightPanel" not in source
    assert "ColourReplayController" not in source
    assert "REPLAY_SPEEDS" not in source


def test_dead_vision_tester_layers_stay_removed() -> None:
    removed = {
        "area_overlay_toggle.py",
        "colour_delete_undo.py",
        "colour_recording.py",
        "colour_replay.py",
        "colour_view_cleanup.py",
        "common.py",
        "enhanced_colour_page.py",
        "hotkey_fix.py",
        "hp_stoplight_monitor.py",
        "image_page.py",
        "manual_colour_save.py",
        "prayer_stoplight_monitor.py",
        "replay_palette_builder.py",
        "replay_reset.py",
        "stoplight_panel.py",
    }
    directory = ROOT / "tools" / "vision_tester"
    assert not any((directory / name).exists() for name in removed)


def test_template_and_sensor_features_use_explicit_page_modules() -> None:
    assert SearchableTemplatePage.__bases__ == (TemplatePage,)
    assert EnhancedSensorPage.__bases__ == (SensorPage,)


def test_modern_ui_is_only_a_compatibility_facade() -> None:
    source = _source("tools/vision_tester/modern_ui.py")
    assert "class ColourPage" not in source
    assert "class TemplatePage" not in source
    assert "class SensorPage" not in source
    assert "match_template(" not in source
    assert "calculate_color_score(" not in source
    assert len(source.splitlines()) < 100


def test_modern_ui_dependency_cannot_spread() -> None:
    directory = ROOT / "tools" / "vision_tester"
    offenders = {
        path.name
        for path in directory.glob("*.py")
        if path.name != "modern_ui.py" and "modern_ui" in path.read_text(encoding="utf-8")
    }
    assert offenders == set()


def test_definition_registry_lives_with_definitions() -> None:
    adapter = _source("tools/definition_tester/registry.py")
    canonical = _source("definitions/registry.py")
    assert "from definitions.registry import" in adapter
    assert "DefinitionEntry(" not in adapter
    assert "DEFINITIONS:" in canonical


def test_architecture_document_names_canonical_owners() -> None:
    architecture = _source("ARCHITECTURE.md")
    for owner in (
        "core/vision/template_analysis.py",
        "core/vision/colour_analysis.py",
        "core/mouse_actions.py",
        "definitions/registry.py",
        "tools/vision_tester/",
    ):
        assert owner in architecture


def test_production_vision_app_has_no_runtime_installers() -> None:
    assert "install_" not in _source("tools/vision_tester/app.py")


def test_colour_page_never_bypasses_the_inheritance_chain() -> None:
    source = _source("tools/vision_tester/colour_page.py")
    assert "ToleranceColourPage._" not in source
    assert "unified_plus._" not in source


def test_template_page_uses_core_template_analysis() -> None:
    source = _source("tools/vision_tester/template_page.py")
    assert "analyse_template(" in source
    assert "match_template(" not in source
    assert "calculate_color_score(" not in source


def test_template_plus_adds_ui_without_reimplementing_matching() -> None:
    source = _source("tools/vision_tester/template_plus.py")
    assert "def _analyse(" not in source
    assert "match_template(" not in source
    assert "calculate_color_score(" not in source


def test_colour_analysis_implementation_lives_in_core() -> None:
    adapter = _source("tools/vision_tester/colour_debug.py")
    assert "core.vision.colour_analysis" in adapter
    assert "cv2." not in adapter
    assert "np." not in adapter


def test_colour_preset_metadata_storage_lives_in_core() -> None:
    for relative_path in (
        "tools/vision_tester/unified_plus.py",
        "tools/vision_tester/colour_browser.py",
        "tools/vision_tester/colour_page.py",
    ):
        source = _source(relative_path)
        assert "colour_preset_meta.json" not in source
        assert "_load_meta" not in source
        assert "_save_meta" not in source


def test_cleaned_vision_modules_have_no_compatibility_installers() -> None:
    for relative_path in (
        "tools/vision_tester/colour_browser.py",
        "tools/vision_tester/colour_page.py",
        "tools/vision_tester/template_plus.py",
        "tools/vision_tester/unified_plus.py",
    ):
        assert "def install_" not in _source(relative_path)


def test_sensor_logic_stays_out_of_vision() -> None:
    vision_files = {
        path.name for path in (ROOT / "core" / "vision").glob("*.py")
    }
    assert not any("sensor" in name or "stoplight" in name for name in vision_files)

    forbidden_imports = (
        "core.vision.hp_sensor",
        "core.vision.hp_stoplight",
        "core.vision.prayer_sensor",
        "core.vision.prayer_stoplight",
        "core.vision.skilling_sensor",
    )
    this_file = Path(__file__).resolve()
    offenders = []
    for path in ROOT.rglob("*.py"):
        if path.resolve() == this_file:
            continue
        source = path.read_text(encoding="utf-8")
        if any(import_path in source for import_path in forbidden_imports):
            offenders.append(str(path.relative_to(ROOT)))
    assert offenders == []


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
