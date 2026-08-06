from __future__ import annotations

import importlib


is_bank_closed_module = importlib.import_module("definitions.bank.is_bank_closed")


def test_bank_closed_is_inverse_of_bank_open(monkeypatch) -> None:
    monkeypatch.setattr(
        is_bank_closed_module,
        "is_bank_open",
        lambda _bot_id: True,
    )
    assert is_bank_closed_module.is_bank_closed() is False

    monkeypatch.setattr(
        is_bank_closed_module,
        "is_bank_open",
        lambda _bot_id: False,
    )
    assert is_bank_closed_module.is_bank_closed() is True
