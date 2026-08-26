from __future__ import annotations

import importlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any


DEFINITIONS_ROOT = Path(__file__).resolve().parents[2] / "definitions"


@dataclass(frozen=True)
class TargetInfo:
    name: str
    module_name: str
    source_path: str
    values: tuple[tuple[str, Any], ...]


def _display_name(path: Path) -> str:
    relative = path.relative_to(DEFINITIONS_ROOT).with_suffix("")
    parts = relative.parts
    category = " / ".join(part.replace("_", " ").title() for part in parts[:-1])
    target = parts[-1].removesuffix("_target").replace("_", " ").title()

    if category.casefold() == target.casefold():
        return category
    return f"{category} / {target}" if category else target


def _module_name(path: Path) -> str:
    relative = path.relative_to(DEFINITIONS_ROOT.parent).with_suffix("")
    return ".".join(relative.parts)


def _public_constants(module) -> tuple[tuple[str, Any], ...]:
    return tuple(
        (name, getattr(module, name))
        for name in sorted(dir(module))
        if name.isupper() and not name.startswith("_")
    )


def discover_targets() -> tuple[TargetInfo, ...]:
    """Return production target constants from all ``*_target.py`` modules."""
    targets: list[TargetInfo] = []

    for path in sorted(DEFINITIONS_ROOT.rglob("*_target.py")):
        module_name = _module_name(path)
        module = importlib.import_module(module_name)
        targets.append(
            TargetInfo(
                name=_display_name(path),
                module_name=module_name,
                source_path=str(path.relative_to(DEFINITIONS_ROOT.parent)),
                values=_public_constants(module),
            )
        )

    return tuple(sorted(targets, key=lambda target: target.name.casefold()))


__all__ = ["TargetInfo", "discover_targets"]
