import numpy as np

from core.vision import api
from core.vision.models import TemplateSettings


def test_image_capture_keeps_area_and_bot_together(monkeypatch):
    calls = []
    screenshot = np.zeros((20, 30, 3), dtype=np.uint8)
    template_rgb = np.zeros((5, 5, 3), dtype=np.uint8)
    template_gray = np.zeros((5, 5), dtype=np.uint8)

    def fake_capture_area(area, bot_id):
        calls.append((area, bot_id))
        return screenshot, (1958, 200, 30, 20)

    monkeypatch.setattr(api, "capture_area", fake_capture_area)
    monkeypatch.setattr(
        api,
        "load_settings",
        lambda _name: TemplateSettings(
            method="TM_CCOEFF_NORMED",
            min_shape=85.0,
            min_color=60.0,
            area="Inventory_Area",
        ),
    )
    monkeypatch.setattr(api, "load_template", lambda _name: (template_rgb, template_gray))

    result = api._capture_for("item", None, bot_id=2)

    assert calls == [("Inventory_Area", 2)]
    assert result[4] == (1958, 200)


def test_click_image_uses_absolute_hit_without_second_offset(monkeypatch):
    moved_to = []
    clicked = []

    class FakeHit:
        def random_point(self, padding):
            assert padding == 4
            return 2010, 250

    monkeypatch.setattr(api, "get_section", lambda _section: {"click_padding_px": 4})
    monkeypatch.setattr(api, "find_image", lambda *_args, **_kwargs: FakeHit())
    monkeypatch.setattr(api.mouse, "move_to", lambda x, y: moved_to.append((x, y)))
    monkeypatch.setattr(api.mouse, "click", lambda button="left": clicked.append(button))

    assert api.click_image("item", area="Inventory_Area", bot_id=2)
    assert moved_to == [(2010, 250)]
    assert clicked == ["left"]
