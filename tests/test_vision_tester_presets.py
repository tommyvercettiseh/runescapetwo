from tools.vision_tester.preset_ui import filter_preset_names, format_ranges


def test_filter_preset_names_returns_all_without_query():
    names = ["cyan", "bank_cyan", "red"]

    assert filter_preset_names(names, "") == names


def test_filter_preset_names_uses_partial_case_insensitive_search():
    names = ["cyan", "bank_cyan", "bank_red"]

    assert filter_preset_names(names, "CYAN") == ["cyan", "bank_cyan"]


def test_filter_preset_names_supports_multiple_terms():
    names = ["cyan", "bank_cyan", "bank_red"]

    assert filter_preset_names(names, "bank cyan") == ["bank_cyan"]


def test_format_ranges_handles_empty_selection():
    assert format_ranges(()) == "No colour selected."


def test_format_ranges_shows_hsv_bounds():
    ranges = (((80, 100, 120), (90, 200, 240)),)

    assert format_ranges(ranges) == "H 80-90  S 100-200  V 120-240"
