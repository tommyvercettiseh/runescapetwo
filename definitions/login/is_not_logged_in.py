from __future__ import annotations

from definitions.login.is_logged_in import is_logged_in


def is_not_logged_in(bot_id: int = 1) -> bool:
    """Return True whenever the normal logged-in HUD is not detected."""
    return not is_logged_in(bot_id)


__all__ = ["is_not_logged_in"]
