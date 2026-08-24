from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_colour_workspace_keeps_the_approved_core_surfaces() -> None:
    source = _source("tools/vision_tester/colour_page.py")
    for label in (
        "COLOURS",
        "AREAS",
        "DETECTION RANGE (PX)",
        "COLOUR TOLERANCE",
        "LIVE AREA",
        "ISOLATED COLOUR",
        "Pipette",
        "Move colour",
        "Click colour",
    ):
        assert label in source


def test_colour_workspace_excludes_old_replay_and_sensor_clutter() -> None:
    source = _source("tools/vision_tester/colour_page.py")
    for forbidden in (
        "ColourReplayController",
        "StoplightPanel",
        "Record Raw",
        "Play Video",
        "Reset Replay",
        "HP:",
        "PRAYER:",
    ):
        assert forbidden not in source


def test_colour_workspace_uses_source_state_instead_of_hidden_source_widgets() -> None:
    controls = _source("tools/vision_tester/source_controls.py")
    page = _source("tools/vision_tester/colour_page.py")
    assert "class SourceState" in controls
    assert "self.source = SourceState(" in page
