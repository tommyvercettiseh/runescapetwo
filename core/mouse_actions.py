from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal

from . import mouse
from .mouse_engine import MouseEngineError
from .targeting import (
    area_target_bounds,
    image_target_bounds,
    validate_area_edge_padding,
    validate_image_edge_padding,
)
from .vision.api import find_image
from .vision.areas import get_region
from .vision.colour_detection import find_colour
from .vision.models import ColourBlob, Hit


# =============================================================================
# PUBLIC TYPES AND RESULTS
# =============================================================================

DEFAULT_AREA_NAME = "Bot_Area_Full"
MouseButton = Literal["left", "right"]
TargetBounds = tuple[int, int, int, int]


@dataclass(frozen=True)
class MouseActionResult:
    """Readable outcome for logging, retries and production fail-safes."""

    success: bool
    action: str
    message: str
    target_name: str | None = None
    position: tuple[int, int] | None = None
    bounds: TargetBounds | None = None
    engine: str = "none"
    fallback_used: bool = False
    blob_pixels: int | None = None
    error: str | None = None

    def __bool__(self) -> bool:
        return self.success


# =============================================================================
# SHARED INTERNAL HELPERS
# =============================================================================

EXPECTED_ACTION_ERRORS = (
    FileNotFoundError,
    KeyError,
    ValueError,
    MouseEngineError,
    mouse.MouseRuntimeError,
)


def _validate_button(button: str) -> MouseButton:
    if button == "left":
        return "left"
    if button == "right":
        return "right"
    raise ValueError("button must be 'left' or 'right'")


def _validate_target_shift(maximum_target_shift: float) -> None:
    if not math.isfinite(float(maximum_target_shift)) or maximum_target_shift < 0:
        raise ValueError("maximum_target_shift must be a non-negative number")


def _find_target_image(
    image_name: str,
    *,
    area_name: str,
    bot_id: int,
) -> Hit | None:
    return find_image(image_name, area=area_name, bot_id=bot_id)


def _validate_blob_settings(
    minimum_blob_pixels: int,
    maximum_blob_pixels: int | None,
    blob_edge_padding: int,
) -> None:
    for name, value in (
        ("minimum_blob_pixels", minimum_blob_pixels),
        ("blob_edge_padding", blob_edge_padding),
    ):
        if isinstance(value, bool) or not isinstance(value, int):
            raise TypeError(f"{name} must be a whole number")
    if minimum_blob_pixels < 1:
        raise ValueError("minimum_blob_pixels must be at least 1")
    if blob_edge_padding < 0:
        raise ValueError("blob_edge_padding cannot be negative")
    if maximum_blob_pixels is not None:
        if isinstance(maximum_blob_pixels, bool) or not isinstance(
            maximum_blob_pixels,
            int,
        ):
            raise TypeError("maximum_blob_pixels must be a whole number or None")
        if maximum_blob_pixels < minimum_blob_pixels:
            raise ValueError(
                "maximum_blob_pixels cannot be smaller than minimum_blob_pixels"
            )


def _image_bounds(hit: Hit, image_edge_padding: float) -> TargetBounds:
    validate_image_edge_padding(image_edge_padding)
    return image_target_bounds(
        hit.x,
        hit.y,
        hit.x + hit.width,
        hit.y + hit.height,
        image_edge_padding=image_edge_padding,
    )


def _colour_bounds(blob: ColourBlob, blob_edge_padding: int) -> TargetBounds:
    """Return an axis-aligned square guaranteed to fit in the blob's safe circle."""
    safe_x, safe_y = blob.safe_point
    safe_radius = max(0.0, float(blob.safe_radius) - blob_edge_padding)
    half_side = max(0, int(math.floor(safe_radius / math.sqrt(2.0))))
    return (
        safe_x - half_side,
        safe_y - half_side,
        safe_x + half_side + 1,
        safe_y + half_side + 1,
    )


def _area_bounds(
    area_name: str,
    *,
    bot_id: int,
    area_edge_padding: int,
) -> TargetBounds:
    x, y, width, height = get_region(area_name, bot_id=bot_id)
    return area_target_bounds(
        x,
        y,
        x + width,
        y + height,
        area_edge_padding=area_edge_padding,
    )


def _center(bounds: TargetBounds) -> tuple[float, float]:
    left, top, right, bottom = bounds
    return (left + right) / 2.0, (top + bottom) / 2.0


def _target_shift(first: TargetBounds, second: TargetBounds) -> float:
    first_x, first_y = _center(first)
    second_x, second_y = _center(second)
    return math.hypot(second_x - first_x, second_y - first_y)


def _point_inside(position: tuple[int, int], bounds: TargetBounds) -> bool:
    x, y = position
    left, top, right, bottom = bounds
    return left <= x < right and top <= y < bottom


def _failure(
    action: str,
    message: str,
    *,
    target_name: str | None = None,
    bounds: TargetBounds | None = None,
    error: str | None = None,
    blob_pixels: int | None = None,
    include_execution_status: bool = False,
) -> MouseActionResult:
    status = (
        mouse.last_execution_status()
        if include_execution_status
        else mouse.MouseExecutionStatus(engine="none")
    )
    return MouseActionResult(
        success=False,
        action=action,
        message=message,
        target_name=target_name,
        position=mouse.position(),
        bounds=bounds,
        engine=status.engine,
        fallback_used=status.fallback_used,
        blob_pixels=blob_pixels,
        error=error,
    )


def _success(
    action: str,
    message: str,
    *,
    target_name: str | None = None,
    bounds: TargetBounds | None = None,
    blob_pixels: int | None = None,
) -> MouseActionResult:
    position = mouse.position()
    status = mouse.last_execution_status()
    if bounds is not None and not _point_inside(position, bounds):
        mouse.cancel_pending_click()
        return MouseActionResult(
            success=False,
            action=action,
            message="Muis eindigde buiten de veilige targetzone.",
            target_name=target_name,
            position=position,
            bounds=bounds,
            engine=status.engine,
            fallback_used=status.fallback_used,
            blob_pixels=blob_pixels,
            error="Final mouse position is outside target bounds",
        )
    return MouseActionResult(
        success=True,
        action=action,
        message=message,
        target_name=target_name,
        position=position,
        bounds=bounds,
        engine=status.engine,
        fallback_used=status.fallback_used,
        blob_pixels=blob_pixels,
        error=status.error,
    )


def _operational_failure(
    action: str,
    target_name: str,
    error: BaseException,
    *,
    bounds: TargetBounds | None = None,
    blob_pixels: int | None = None,
) -> MouseActionResult:
    return _failure(
        action,
        f"{action} mislukt: {error}",
        target_name=target_name,
        bounds=bounds,
        error=str(error),
        blob_pixels=blob_pixels,
        include_execution_status=True,
    )


# =============================================================================
# IMAGE ACTIONS: MOVE TO IMAGE AND CLICK IMAGE
# =============================================================================

# Voorbeeld in scripts:
# result = mouse_actions.move_to_image(
#     image_name="Logs",
#     area_name="Bot_Area_Full",
#     bot_id=1,
#     image_edge_padding=20,
# )
# if not result:
#     print(result.message)
def move_to_image(
    image_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    image_edge_padding: float = 20,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Move to an image and prepare one short-lived separate click."""
    validate_image_edge_padding(image_edge_padding)
    try:
        hit = _find_target_image(
            image_name,
            area_name=area_name,
            bot_id=bot_id,
        )
        if hit is None:
            return _failure(
                "move_to_image",
                f"Image niet gevonden: {image_name}",
                target_name=image_name,
            )
        bounds = _image_bounds(hit, image_edge_padding)
        with mouse.action_guard():
            mouse.move_to_target(
                *bounds,
                require_external=require_external_mouse,
                keep_pending_click=True,
            )
            return _success(
                "move_to_image",
                "Muis staat op de image; losse click is maximaal "
                f"{mouse.PENDING_CLICK_TIMEOUT_S:g} seconden beschikbaar.",
                target_name=image_name,
                bounds=bounds,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure("move_to_image", image_name, error)


# Voorbeeld in scripts:
# result = mouse_actions.click_image(
#     image_name="Logs",
#     area_name="Bot_Area_Full",
#     bot_id=1,
#     button="right",
#     image_edge_padding=20,
#     confirm_before_click=True,
# )
def click_image(
    image_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    button: MouseButton = "left",
    image_edge_padding: float = 20,
    confirm_before_click: bool = False,
    maximum_target_shift: float = 12,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Find, move and click as one serialized action."""
    selected_button = _validate_button(button)
    validate_image_edge_padding(image_edge_padding)
    _validate_target_shift(maximum_target_shift)

    bounds: TargetBounds | None = None
    try:
        hit = _find_target_image(
            image_name,
            area_name=area_name,
            bot_id=bot_id,
        )
        if hit is None:
            return _failure(
                "click_image",
                f"Image niet gevonden: {image_name}",
                target_name=image_name,
            )
        bounds = _image_bounds(hit, image_edge_padding)

        with mouse.action_guard():
            if confirm_before_click:
                mouse.move_to_target(
                    *bounds,
                    require_external=require_external_mouse,
                    keep_pending_click=False,
                )
                confirmed_hit = _find_target_image(
                    image_name,
                    area_name=area_name,
                    bot_id=bot_id,
                )
                if confirmed_hit is None:
                    return _failure(
                        "click_image",
                        "Image verdween tijdens de muisbeweging; er is niet geklikt.",
                        target_name=image_name,
                        bounds=bounds,
                        include_execution_status=True,
                    )
                confirmed_bounds = _image_bounds(confirmed_hit, image_edge_padding)
                shift = _target_shift(bounds, confirmed_bounds)
                if shift > maximum_target_shift:
                    return _failure(
                        "click_image",
                        f"Image verschoof {shift:.1f}px; er is niet geklikt.",
                        target_name=image_name,
                        bounds=confirmed_bounds,
                        include_execution_status=True,
                    )
                bounds = confirmed_bounds

            mouse.move_and_click_target(
                *bounds,
                button=selected_button,
                require_external=require_external_mouse,
            )
            return _success(
                "click_image",
                f"Image geklikt met {selected_button}.",
                target_name=image_name,
                bounds=bounds,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure(
            "click_image",
            image_name,
            error,
            bounds=bounds,
        )


# =============================================================================
# COLOUR ACTIONS: MOVE TO COLOUR AND CLICK COLOUR
# =============================================================================

# Voorbeeld in scripts:
# result = mouse_actions.move_to_colour(
#     colour_name="cyan",
#     area_name="Bot_Area_Full",
#     minimum_blob_pixels=500,
#     maximum_blob_pixels=15000,
# )
def move_to_colour(
    colour_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    minimum_blob_pixels: int = 20,
    maximum_blob_pixels: int | None = None,
    blob_edge_padding: int = 1,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Move to the safest inner zone of the largest valid colour blob."""
    _validate_blob_settings(
        minimum_blob_pixels,
        maximum_blob_pixels,
        blob_edge_padding,
    )
    bounds: TargetBounds | None = None
    blob: ColourBlob | None = None
    try:
        blob = find_colour(
            colour_name,
            area=area_name,
            bot_id=bot_id,
            minimum_area_px=minimum_blob_pixels,
            maximum_area_px=maximum_blob_pixels,
        )
        if blob is None:
            return _failure(
                "move_to_colour",
                f"Geen geldige kleurblob gevonden: {colour_name}",
                target_name=colour_name,
            )
        bounds = _colour_bounds(blob, blob_edge_padding)
        with mouse.action_guard():
            mouse.move_to_target(
                *bounds,
                require_external=require_external_mouse,
                keep_pending_click=True,
            )
            return _success(
                "move_to_colour",
                f"Muis staat in een kleurblob van {blob.area_px} pixels.",
                target_name=colour_name,
                bounds=bounds,
                blob_pixels=blob.area_px,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure(
            "move_to_colour",
            colour_name,
            error,
            bounds=bounds,
            blob_pixels=None if blob is None else blob.area_px,
        )


# Voorbeeld in scripts:
# result = mouse_actions.click_colour(
#     colour_name="cyan",
#     area_name="Bot_Area_Full",
#     button="left",
#     minimum_blob_pixels=500,
#     maximum_blob_pixels=15000,
# )
def click_colour(
    colour_name: str,
    *,
    area_name: str = DEFAULT_AREA_NAME,
    bot_id: int = 1,
    button: MouseButton = "left",
    minimum_blob_pixels: int = 20,
    maximum_blob_pixels: int | None = None,
    blob_edge_padding: int = 1,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Find the largest valid colour blob, move and click atomically."""
    selected_button = _validate_button(button)
    _validate_blob_settings(
        minimum_blob_pixels,
        maximum_blob_pixels,
        blob_edge_padding,
    )
    bounds: TargetBounds | None = None
    blob: ColourBlob | None = None
    try:
        blob = find_colour(
            colour_name,
            area=area_name,
            bot_id=bot_id,
            minimum_area_px=minimum_blob_pixels,
            maximum_area_px=maximum_blob_pixels,
        )
        if blob is None:
            return _failure(
                "click_colour",
                f"Geen geldige kleurblob gevonden: {colour_name}",
                target_name=colour_name,
            )
        bounds = _colour_bounds(blob, blob_edge_padding)
        with mouse.action_guard():
            mouse.move_and_click_target(
                *bounds,
                button=selected_button,
                require_external=require_external_mouse,
            )
            return _success(
                "click_colour",
                f"Kleurblob van {blob.area_px} pixels geklikt met {selected_button}.",
                target_name=colour_name,
                bounds=bounds,
                blob_pixels=blob.area_px,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure(
            "click_colour",
            colour_name,
            error,
            bounds=bounds,
            blob_pixels=None if blob is None else blob.area_px,
        )


# =============================================================================
# AREA ACTIONS: MOVE TO AREA AND CLICK IN AREA
# =============================================================================

# Voorbeeld in scripts:
# result = mouse_actions.move_to_area(
#     area_name="Inventory_Area",
#     bot_id=1,
#     area_edge_padding=8,
# )
def move_to_area(
    area_name: str,
    *,
    bot_id: int = 1,
    area_edge_padding: int = 0,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Move inside an area and prepare one short-lived separate click."""
    validate_area_edge_padding(area_edge_padding)
    bounds: TargetBounds | None = None
    try:
        bounds = _area_bounds(
            area_name,
            bot_id=bot_id,
            area_edge_padding=area_edge_padding,
        )
        with mouse.action_guard():
            mouse.move_to_target(
                *bounds,
                require_external=require_external_mouse,
                keep_pending_click=True,
            )
            return _success(
                "move_to_area",
                "Muis staat in de area; losse click is maximaal "
                f"{mouse.PENDING_CLICK_TIMEOUT_S:g} seconden beschikbaar.",
                target_name=area_name,
                bounds=bounds,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure(
            "move_to_area",
            area_name,
            error,
            bounds=bounds,
        )


# Voorbeeld in scripts:
# result = mouse_actions.click_in_area(
#     area_name="Inventory_Area",
#     bot_id=1,
#     button="right",
#     area_edge_padding=8,
# )
def click_in_area(
    area_name: str,
    *,
    bot_id: int = 1,
    button: MouseButton = "left",
    area_edge_padding: int = 0,
    require_external_mouse: bool = True,
) -> MouseActionResult:
    """Move and click inside an area as one serialized action."""
    selected_button = _validate_button(button)
    validate_area_edge_padding(area_edge_padding)
    bounds: TargetBounds | None = None
    try:
        bounds = _area_bounds(
            area_name,
            bot_id=bot_id,
            area_edge_padding=area_edge_padding,
        )
        with mouse.action_guard():
            mouse.move_and_click_target(
                *bounds,
                button=selected_button,
                require_external=require_external_mouse,
            )
            return _success(
                "click_in_area",
                f"Area geklikt met {selected_button}.",
                target_name=area_name,
                bounds=bounds,
            )
    except EXPECTED_ACTION_ERRORS as error:
        return _operational_failure(
            "click_in_area",
            area_name,
            error,
            bounds=bounds,
        )


# =============================================================================
# CLICK CURRENT POSITION AFTER MOVE TO IMAGE OR MOVE TO AREA
# =============================================================================

# Voorbeeld in scripts:
# moved = mouse_actions.move_to_image(image_name="Logs")
# if moved:
#     clicked = mouse_actions.click(button="left")
#     if not clicked:
#         print(clicked.message)
def click(
    *,
    button: MouseButton = "left",
    require_previous_move: bool = True,
) -> MouseActionResult:
    """Click the position prepared by move_to_image or move_to_area."""
    selected_button = _validate_button(button)
    with mouse.action_guard():
        if require_previous_move and not mouse.has_pending_click():
            return _failure(
                "click",
                "Geen geldige voorbereidende move gevonden; er is niet geklikt.",
            )
        try:
            mouse.click(
                selected_button,
                require_pending=require_previous_move,
            )
            return _success(
                "click",
                f"Huidige muispositie geklikt met {selected_button}.",
            )
        except EXPECTED_ACTION_ERRORS as error:
            return _operational_failure("click", "current_position", error)


# =============================================================================
# FAIL-SAFES AND MANUAL CONTROL
# =============================================================================

def cancel_pending_click() -> bool:
    """Cancel the click prepared by a separate move action."""
    return mouse.cancel_pending_click()


def emergency_stop() -> None:
    """Request an immediate stop; the executor safely releases the button."""
    mouse.request_emergency_stop()


def reset_emergency_stop() -> None:
    """Allow mouse actions again after the cause of the stop was checked."""
    mouse.reset_emergency_stop()


__all__ = [
    "MouseActionResult",
    "MouseButton",
    "move_to_image",
    "click_image",
    "move_to_colour",
    "click_colour",
    "move_to_area",
    "click_in_area",
    "click",
    "cancel_pending_click",
    "emergency_stop",
    "reset_emergency_stop",
]
