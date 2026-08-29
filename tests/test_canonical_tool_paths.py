from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _source(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_image_tester_uses_canonical_template_analysis() -> None:
    source = _source("tools/image_tester/app.py")
    assert "analyse_template(" in source
    assert "match_template(" not in source
    assert "iter_candidates(" not in source
    assert "calculate_color_score(" not in source


def test_dead_image_tester_gui_stays_removed() -> None:
    assert not (ROOT / "tools" / "image_tester" / "gui.py").exists()


def test_definition_tester_registry_is_only_an_adapter() -> None:
    source = _source("tools/definition_tester/registry.py")
    assert "from definitions.registry import" in source
    assert "DefinitionEntry(" not in source
