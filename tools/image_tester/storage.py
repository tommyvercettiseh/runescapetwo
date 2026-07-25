from __future__ import annotations

from core.vision.models import TemplateSettings
from core.vision.templates import load_metadata, save_settings


def load_template_settings(image_name: str) -> TemplateSettings:
    from core.vision.templates import load_settings

    return load_settings(image_name)


def save_template_settings(
    image_name: str,
    *,
    method: str,
    min_shape: float,
    min_color: float,
    area: str | None = None,
) -> None:
    save_settings(
        image_name,
        TemplateSettings(
            method=method,
            min_shape=float(min_shape),
            min_color=float(min_color),
            area=area,
        ),
    )


def all_metadata() -> dict:
    return load_metadata()
