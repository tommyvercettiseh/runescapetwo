from tools.vision_tester.common import _rounded_rectangle, filter_options


def test_filter_options_matches_any_part_case_insensitively() -> None:
    values = ["inventory_panel", "Game View", "minimap"]

    assert filter_options(values, "VENT") == ["inventory_panel"]
    assert filter_options(values, "view") == ["Game View"]
    assert filter_options(values, "map") == ["minimap"]


def test_filter_options_returns_everything_for_empty_query() -> None:
    values = ["one", "two"]

    assert filter_options(values, "  ") == values


def test_rounded_rectangle_accepts_canvas_outline_width() -> None:
    class FakeCanvas:
        def create_polygon(self, *coordinates, **options):
            self.coordinates = coordinates
            self.options = options
            return 1

    canvas = FakeCanvas()

    _rounded_rectangle(canvas, 116, 36, 12, outline="#000", width=1)

    assert canvas.options["width"] == 1
