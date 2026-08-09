import numpy as np

from core import mouse_actions
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


def test_click_image_delegates_area_and_bot_to_canonical_mouse_action(monkeypatch):
    calls = []
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
    monkeypatch.setattr(
        mouse_actions,
        "click_image",
        lambda **kwargs: calls.append(kwargs) or True,
    )

    assert api.click_image("item", area="Inventory_Area", bot_id=2)
    assert calls == [
        {
            "image_name": "item",
            "area_name": "Inventory_Area",
            "bot_id": 2,
            "button": "left",
        }
    ]
