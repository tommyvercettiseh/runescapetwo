from __future__ import annotations

from dataclasses import dataclass
import ast
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EditableField:
    name: str
    value: Any
    kind: str
    label: str
    unit: str = ""


_FIELD_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("_COLOUR", "colour", "Colour", ""),
    ("_COLOR", "colour", "Colour", ""),
    ("_AREA", "area", "Area", ""),
    ("_MIN_PIXELS", "int", "Minimum grootte", "px"),
    ("_MAX_PIXELS", "int", "Maximum grootte", "px"),
    ("_PADDING", "int", "Rand vermijden", "%"),
    ("_BUTTON", "choice", "Muisknop", ""),
    ("_TIMEOUT", "float", "Timeout", "sec"),
    ("_INTERVAL", "float", "Controle-interval", "sec"),
    ("_IMAGE", "image", "Image", ""),
)


def _field_rule(name: str) -> tuple[str, str, str] | None:
    for suffix, kind, label, unit in _FIELD_RULES:
        if name.endswith(suffix):
            return kind, label, unit
    return None


def read_editable_fields(path: Path) -> list[EditableField]:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    fields: list[EditableField] = []

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name):
            continue
        rule = _field_rule(target.id)
        if rule is None:
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            continue
        if not isinstance(value, (str, int, float, bool)):
            continue
        kind, label, unit = rule
        fields.append(EditableField(target.id, value, kind, label, unit))
    return fields


def update_literal(path: Path, variable_name: str, value: Any) -> None:
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(path))
    target_node: ast.Assign | None = None

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if isinstance(target, ast.Name) and target.id == variable_name:
            target_node = node
            break

    if target_node is None:
        raise KeyError(f"Instelling niet gevonden: {variable_name}")

    lines = source.splitlines(keepends=True)
    line_index = target_node.lineno - 1
    newline = "\n" if lines[line_index].endswith("\n") else ""
    lines[line_index] = f"{variable_name} = {value!r}{newline}"
    path.write_text("".join(lines), encoding="utf-8")
