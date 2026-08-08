from __future__ import annotations

from . import modern_ui


_SENSOR_PAGE = modern_ui.SensorPage
_ORIGINAL_BUILD = _SENSOR_PAGE._build
_ORIGINAL_CHANGED = _SENSOR_PAGE._changed
_ORIGINAL_MEASURE = _SENSOR_PAGE._measure


def _function_label(self) -> str | None:
    check = self.checks.get(self.sensor_name.get())
    if check is None or check.kind != "python_bool":
        return None
    return f"{check.value.rsplit('.', 1)[-1]}()"


def _style_boolean_badge(self, result: bool | None) -> None:
    function_name = _function_label(self)
    if function_name is None:
        return

    if result is True:
        value = "TRUE"
        background = modern_ui.SUCCESS
    elif result is False:
        value = "FALSE"
        background = modern_ui.DANGER
    else:
        value = "—"
        background = modern_ui.BASIC_BORDER if hasattr(modern_ui, "BASIC_BORDER") else modern_ui.BORDER

    self.outcome.configure(
        text=f"{function_name}    {value}",
        text_color="white" if result is not None else modern_ui.TEXT,
        fg_color=background,
        corner_radius=8,
        width=260,
        height=38,
        padx=14,
    )


def _build_with_boolean_badge(self) -> None:
    _ORIGINAL_BUILD(self)
    # Keep the existing result row, but make the right-hand outcome label a
    # compact boolean sensor card rather than a loose TRUE/FALSE word.
    self.outcome.configure(width=260, height=38, corner_radius=8, padx=14)


def _changed_with_boolean_badge(self) -> None:
    _ORIGINAL_CHANGED(self)
    if _function_label(self) is not None:
        _style_boolean_badge(self, None)


def _measure_with_boolean_badge(self) -> None:
    _ORIGINAL_MEASURE(self)
    if _function_label(self) is None:
        return

    text = str(self.outcome.cget("text")).strip().upper()
    if text == "TRUE":
        _style_boolean_badge(self, True)
    elif text == "FALSE":
        _style_boolean_badge(self, False)


def install_sensor_boolean_badge() -> None:
    _SENSOR_PAGE._build = _build_with_boolean_badge
    _SENSOR_PAGE._changed = _changed_with_boolean_badge
    _SENSOR_PAGE._measure = _measure_with_boolean_badge


__all__ = ["install_sensor_boolean_badge"]
