from tools.vision_tester.common import filter_options


def test_filter_options_matches_any_part_case_insensitively() -> None:
    values = ["inventory_panel", "Game View", "minimap"]

    assert filter_options(values, "VENT") == ["inventory_panel"]
    assert filter_options(values, "view") == ["Game View"]
    assert filter_options(values, "map") == ["minimap"]


def test_filter_options_returns_everything_for_empty_query() -> None:
    values = ["one", "two"]

    assert filter_options(values, "  ") == values
