import importlib
from types import SimpleNamespace


prayer_module = importlib.import_module("definitions.prayer.is_low_prayer")


def test_is_low_prayer_uses_profile_area_and_sensor(monkeypatch):
    frame = object()
    calls = []

    monkeypatch.setattr(
        prayer_module,
        "load_prayer_stoplight_profile",
        lambda: {"area": "Prayer_Custom"},
    )

    def fake_capture_area(area, *, bot_id=None):
        calls.append((area, bot_id))
        return frame, (0, 0, 1, 1)

    monkeypatch.setattr(prayer_module, "capture_area", fake_capture_area)
    monkeypatch.setattr(
        prayer_module,
        "classify_prayer_frame",
        lambda received: SimpleNamespace(low=received is frame),
    )

    assert prayer_module.is_low_prayer(bot_id=2) is True
    assert calls == [("Prayer_Custom", 2)]


def test_is_low_prayer_unknown_is_false(monkeypatch):
    class UnknownReading:
        @property
        def low(self):
            raise ValueError("unknown")

    monkeypatch.setattr(prayer_module, "load_prayer_stoplight_profile", lambda: {})
    monkeypatch.setattr(
        prayer_module,
        "capture_area",
        lambda area, *, bot_id=None: (object(), (0, 0, 1, 1)),
    )
    monkeypatch.setattr(prayer_module, "classify_prayer_frame", lambda _frame: UnknownReading())

    assert prayer_module.is_low_prayer() is False
