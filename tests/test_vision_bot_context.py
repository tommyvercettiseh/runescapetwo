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
    targets = []

    class FakeHit:
        x = 2000
        y = 240
        width = 20
        height = 20

    monkeypatch.setattr(api, "get_section", lambda _section: {"click_padding_px": 4})
    monkeypatch.setattr(api, "find_image", lambda *_args, **_kwargs: FakeHit())
    monkeypatch.setattr(
        api.mouse,
        "move_and_click_target",
        lambda *args, **kwargs: targets.append((args, kwargs)),
    )

    assert api.click_image("item", area="Inventory_Area", bot_id=2)
    assert targets == [
        ((2000, 240, 2020, 260), {"padding_px": 4, "button": "left"})
    ]
