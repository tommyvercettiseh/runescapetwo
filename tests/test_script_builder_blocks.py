from tools.definition_tester.registry import DEFINITIONS
from tools.unified_tester.action_registry import action_names


def test_script_builder_exposes_conditional_sensors():
    names = {(entry.category, entry.name) for entry in DEFINITIONS}

    assert ("Login", "Not logged in.") in names
    assert ("Camera", "Compass north missing.") in names
    assert ("Camera", "Compass east missing.") in names
    assert ("Camera", "Compass south missing.") in names
    assert ("Camera", "Compass west missing.") in names


def test_script_builder_exposes_generic_actions():
    names = set(action_names())

    assert "Login" in names
    assert "Click area" in names
