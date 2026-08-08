from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any


def result_success(result: Any) -> bool | None:
    """Return a normalized success state without forcing unknown results to pass."""
    if isinstance(result, bool):
        return result

    success = getattr(result, "success", None)
    if isinstance(success, bool):
        return success

    if isinstance(result, dict):
        success = result.get("success")
        if isinstance(success, bool):
            return success

    return None


def result_detail(result: Any) -> str:
    message = getattr(result, "message", "")
    return str(message) if message else ""


def format_result(result: Any) -> str:
    if isinstance(result, bool):
        return f"RESULT: {'TRUE' if result else 'FALSE'}"
    if result is None:
        return "RESULT: None"
    if is_dataclass(result):
        return "\n".join(
            f"{key}: {value}" for key, value in asdict(result).items()
        )
    if isinstance(result, dict):
        return "\n".join(f"{key}: {value}" for key, value in result.items())
    if isinstance(result, (list, tuple, set)):
        return "\n".join(map(str, result)) or "Empty result."
    return repr(result)


__all__ = ["format_result", "result_detail", "result_success"]
