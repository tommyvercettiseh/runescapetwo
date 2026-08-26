from __future__ import annotations

from definitions.bank import bank_target
from tools.unified_tester.target_inspector import discover_targets


def test_bank_target_is_discovered_from_production_module() -> None:
    targets = {target.name: target for target in discover_targets()}

    assert "Bank" in targets
    bank = targets["Bank"]
    values = dict(bank.values)

    assert bank.source_path.replace("\\", "/") == "definitions/bank/bank_target.py"
    assert values["BANK_AREA"] == bank_target.BANK_AREA
    assert values["BANK_COLOUR"] == bank_target.BANK_COLOUR
    assert values["BANK_MIN_PIXELS"] == bank_target.BANK_MIN_PIXELS
    assert values["BANK_MAX_PIXELS"] == bank_target.BANK_MAX_PIXELS
