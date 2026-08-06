from __future__ import annotations

import importlib

import pytest


bank_inventory_module = importlib.import_module("actions.bank.bank_inventory")


@pytest.fixture(autouse=True)
def bank_all_selected_by_default(monkeypatch):
    """Keep unrelated banking tests independent from a live BankAllSelected image."""
    monkeypatch.setattr(
        bank_inventory_module,
        "is_bank_all_selected",
        lambda _bot_id: True,
    )
