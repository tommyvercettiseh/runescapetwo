from __future__ import annotations

import importlib
import os

os.environ.setdefault("PYNPUT_BACKEND", "dummy")


bank_inventory_module = importlib.import_module("actions.bank.bank_inventory")
bank_all_module = importlib.import_module("definitions.bank.is_bank_all_selected")


def test_bank_all_selected_uses_named_template(monkeypatch) -> None:
    calls = []
    marker = object()
    monkeypatch.setattr(
        bank_all_module.vision,
        "find_image",
        lambda **settings: calls.append(settings) or marker,
    )

    assert bank_all_module.is_bank_all_selected(bot_id=3) is True
    assert calls == [
        {
            "image_name": "BankAllSelected",
            "area": "Bot_Area",
            "bot_id": 3,
        }
    ]


def test_bank_all_selected_returns_false_without_match(monkeypatch) -> None:
    monkeypatch.setattr(
        bank_all_module.vision,
        "find_image",
        lambda **_settings: None,
    )

    assert bank_all_module.is_bank_all_selected() is False


def test_bank_inventory_refuses_when_all_is_not_selected(monkeypatch) -> None:
    clicks = []
    monkeypatch.setattr(bank_inventory_module, "is_bank_open", lambda _bot_id: True)
    monkeypatch.setattr(
        bank_inventory_module,
        "is_bank_all_selected",
        lambda _bot_id: False,
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "get_inventory_state",
        lambda _bot_id: (_ for _ in ()).throw(
            AssertionError("inventory may not be scanned before Bank All is confirmed")
        ),
    )
    monkeypatch.setattr(
        bank_inventory_module,
        "click_inventory_slot",
        lambda *args: clicks.append(args) or True,
    )

    result = bank_inventory_module.bank_inventory()

    assert result.success is False
    assert result.bank_open is True
    assert "All" in result.message
    assert clicks == []
