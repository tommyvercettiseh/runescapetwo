from __future__ import annotations

import time

from core.vision.screenshots import capture_area

from . import modern_ui
from .sensor_checks import evaluate_sensor


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
        check = self.checks.get(self.sensor_name.get())
        if check is None or check.kind != "python_bool":
            super()._measure()
            return

        bot_id = int(self.bot_id.get())
        started = time.perf_counter()
        try:
            screenshot, _region = capture_area(check.area, bot_id=bot_id)
            result = evaluate_sensor(check, bot_id=bot_id)

            self.live_view.show(screenshot)
            self.detected_view.show(screenshot.copy())
            self.measurement.configure(
                text=f"Definition resultaat  •  {'TRUE' if result else 'FALSE'}"
            )
            self._style_boolean_badge(result)

            elapsed = (time.perf_counter() - started) * 1000
            self.status.set(
                f"Bot {bot_id}  •  {check.name}  •  {elapsed:.1f} ms"
            )
        except Exception as exc:
            # A transient measurement error should not disable Live mode.
            self._style_boolean_badge(None)
            self.status.set(f"Fout: {exc}")


def install_sensor_boolean_badge() -> None:
    """Compatibility no-op; use EnhancedSensorPage explicitly."""


__all__ = ["EnhancedSensorPage", "install_sensor_boolean_badge"]
