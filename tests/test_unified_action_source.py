from __future__ import annotations

import inspect

from actions.bank.close_bank import close_bank
from definitions.interface.screen_target import SCREEN_CROSS_IMAGE
from tools.unified_tester.action_registry import get_action


def test_screen_cross_uses_existing_production_template() -> None:
    assert SCREEN_CROSS_IMAGE == "Interface_ScreenCross"


def test_close_bank_exposes_real_production_source() -> None:
    spec = get_action("Close bank")

    assert spec.source is close_bank
    source = inspect.getsource(spec.source)
    assert "click_close_screen" in source
    assert "is_bank_open" in source
