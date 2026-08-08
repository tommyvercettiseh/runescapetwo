from __future__ import annotations

from . import modern_ui


class EnhancedSensorPage(modern_ui.SensorPage):
    """Sensor page with a compact function-aware badge for Python booleans."""

    def _build(self) -> None:
        super()._build()
        self.outcome.configure(width=260, height=38, corner_radius=8, padx=14)

    def _function_label(self) -> str | None:
        check = self.checks.get(self.sensor_name.get())
        if check is None or check.kind != "python_bool":
            return None
        return f"{check.value.rsplit('.', 1)[-1]}()"

    def _style_boolean_badge(self, result: bool | None) -> None:
        function_name = self._function_label()
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
            background = modern_ui.BORDER

        self.outcome.configure(
            text=f"{function_name}    {value}",
            text_color="white" if result is not None else modern_ui.TEXT,
            fg_color=background,
            corner_radius=8,
            width=260,
            height=38,
            padx=14,
        )

    def _changed(self) -> None:
        super()._changed()
        if self._function_label() is not None:
            self._style_boolean_badge(None)

    def _measure(self) -> None:
        super()._measure()
        if self._function_label() is None:
            return

        text = str(self.outcome.cget("text")).strip().upper()
        if text == "TRUE":
            self._style_boolean_badge(True)
        elif text == "FALSE":
            self._style_boolean_badge(False)


def install_sensor_boolean_badge() -> None:
    """Compatibility no-op; use EnhancedSensorPage explicitly."""


__all__ = ["EnhancedSensorPage", "install_sensor_boolean_badge"]
