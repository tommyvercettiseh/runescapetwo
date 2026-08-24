from dataclasses import dataclass
from pathlib import Path

from definitions.inventory.constants import INVENTORY_COLUMNS, TOTAL_SLOTS
from definitions.inventory.exclusions import resolve_inventory_exclusions
from tools.unified_tester.action_registry import ACTION_SPECS, action_names, get_action
from tools.unified_tester.result_utils import format_result, result_detail, result_success
from tools.unified_tester.scenario_code_editor import ScenarioCodeEditor
from tools.unified_tester.scenario_runner import BANKING_SCENARIO, STEP_HANDLERS
from tools.vision_tester.colour_browser import BrowserToleranceColourPage
from tools.vision_tester.colour_page import ColourPage
from tools.vision_tester.sensor_boolean_badge import EnhancedSensorPage
from tools.vision_tester.sensor_page import SensorPage
from tools.vision_tester.stoplight_panel import StoplightPanel
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


def test_colour_page_uses_one_operator_page_instead_of_feature_subclasses() -> None:
    assert ColourPage.__bases__ == (BrowserToleranceColourPage,)
    assert issubclass(BrowserToleranceColourPage, ToleranceColourPage)

    legacy_page_names = {
        "ManualColourPage",
        "DeleteUndoColourPage",
        "RecordedColourPage",
        "ReplayResetPage",
        "HpStoplightMonitorPage",
        "PrayerStoplightMonitorPage",
    }
    assert legacy_page_names.isdisjoint(cls.__name__ for cls in ColourPage.__mro__)


def test_stoplight_feedback_is_composed_not_inherited() -> None:
    assert not issubclass(ColourPage, StoplightPanel)
    assert "StoplightPanel(" in _source("tools/vision_tester/colour_page.py")


def test_legacy_colour_feature_modules_are_removed() -> None:
    legacy_modules = {
        "manual_colour_save.py",
        "colour_delete_undo.py",
        "colour_recording.py",
        "replay_reset.py",
        "hp_stoplight_monitor.py",
        "prayer_stoplight_monitor.py",
    }
    directory = ROOT / "tools" / "vision_tester"
    assert not any((directory / name).exists() for name in legacy_modules)


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
