from __future__ import annotations

from collections.abc import Mapping

from .store import EditableArea

ALL_GROUPS = "Alle groepen"


def group_names(areas: Mapping[str, EditableArea]) -> tuple[str, ...]:
    groups = sorted({area.group or "default" for area in areas.values()}, key=str.lower)
    return (ALL_GROUPS, *groups)


def visible_area_names(
    areas: Mapping[str, EditableArea],
    *,
    name_query: str = "",
    group: str = ALL_GROUPS,
) -> tuple[str, ...]:
    query = name_query.strip().lower()
    selected_group = group.strip() or ALL_GROUPS

    names = []
    for name, area in areas.items():
        if selected_group != ALL_GROUPS and (area.group or "default") != selected_group:
            continue
        if query and query not in name.lower():
            continue
        names.append(name)

    return tuple(sorted(names, key=str.lower))
