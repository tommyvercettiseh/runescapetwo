from tools.area_maker.filters import ALL_GROUPS, group_names, visible_area_names
from tools.area_maker.store import EditableArea


def sample_areas() -> dict[str, EditableArea]:
    return {
        "HP_Area": EditableArea("HP_Area", 1, 2, 3, 4, group="Basic"),
        "Inventory_Area": EditableArea("Inventory_Area", 5, 6, 7, 8, group="Inventory"),
        "Inventory_Slot_1": EditableArea("Inventory_Slot_1", 9, 10, 11, 12, group="Inventory_Slots"),
    }


def test_groups_are_unique_sorted_and_include_all() -> None:
    assert group_names(sample_areas()) == (
        ALL_GROUPS,
        "Basic",
        "Inventory",
        "Inventory_Slots",
    )


def test_partial_name_filter_is_case_insensitive() -> None:
    assert visible_area_names(sample_areas(), name_query="inventory") == (
        "Inventory_Area",
        "Inventory_Slot_1",
    )


def test_group_filter_only_returns_that_group() -> None:
    assert visible_area_names(sample_areas(), group="Basic") == ("HP_Area",)


def test_name_and_group_filters_combine() -> None:
    assert visible_area_names(
        sample_areas(),
        name_query="slot",
        group="Inventory_Slots",
    ) == ("Inventory_Slot_1",)
