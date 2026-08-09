import importlib
from types import SimpleNamespace


hp_module = importlib.import_module("definitions.hp.is_low_hp")


def test_is_low_hp_uses_profile_area_and_sensor(monkeypatch):
    frame = object()
    calls = []

    monkeypatch.setattr(
        hp_module,
        "load_hp_stoplight_profile",
        lambda: {"area": "Hp_Custom"},
    )

    def fake_capture_area(area, *, bot_id=None):
        calls.append((area, bot_id))
        return frame, (0, 0, 1, 1)

    monkeypatch.setattr(hp_module, "capture_area", fake_capture_area)
    monkeypatch.setattr(
        hp_module,
        "classify_hp_frame",
        lambda received: SimpleNamespace(low=received is frame),
    )

    assert hp_module.is_low_hp(bot_id=3) is True
    assert calls == [("Hp_Custom", 3)]


def test_is_low_hp_unknown_is_false(monkeypatch):
    class UnknownReading:
        @property
        def low(self):
            raise ValueError("unknown")

    monkeypatch.setattr(hp_module, "load_hp_stoplight_profile", lambda: {})
    monkeypatch.setattr(
        hp_module,
        "capture_area",
        lambda area, *, bot_id=None: (object(), (0, 0, 1, 1)),
    )
    monkeypatch.setattr(hp_module, "classify_hp_frame", lambda _frame: UnknownReading())

    assert hp_module.is_low_hp() is False
