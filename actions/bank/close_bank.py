import time

from actions.interface.click_close_screen import click_close_screen
from core.action_trace import trace
from definitions.bank.bank_target import BANK_DEPOSIT_IMAGE
from definitions.bank.is_bank_open import is_bank_open


BANK_CLOSE_TIMEOUT = 3.0
BANK_CHECK_INTERVAL = 0.20
BANK_CLOSED_CONFIRMATIONS = 3


def close_bank(
    bot_id: int = 1,
    seconds: float = BANK_CLOSE_TIMEOUT,
) -> bool:
    if seconds <= 0:
        raise ValueError("seconds must be greater than 0")

    trace(f"[CHECK] bank open via {BANK_DEPOSIT_IMAGE}")
    bank_open = is_bank_open(bot_id)
    trace(f"[CHECK] bank_open = {bank_open}")
    if not bank_open:
        trace("[OK] bank already closed")
        return True

    trace("[ACTION] close bank interface")
    click_result = click_close_screen(bot_id)
    if not click_result:
        trace("[FAIL] close-screen click failed; bank left unchanged")
        return False

    trace(
        f"[WAIT] {BANK_DEPOSIT_IMAGE} must be absent "
        f"{BANK_CLOSED_CONFIRMATIONS} checks in a row"
    )
    deadline = time.monotonic() + seconds
    confirmations = 0

    while time.monotonic() < deadline:
        if not is_bank_open(bot_id):
            confirmations += 1
            trace(
                f"[CONFIRM] bank closed {confirmations}/"
                f"{BANK_CLOSED_CONFIRMATIONS}"
            )
            if confirmations >= BANK_CLOSED_CONFIRMATIONS:
                trace("[OK] bank closed confirmed")
                return True
        else:
            if confirmations:
                trace("[WAIT] bank visible again; confirmations reset")
            confirmations = 0

        time.sleep(BANK_CHECK_INTERVAL)

    trace("[FAIL] close-bank confirmation timed out")
    return False
