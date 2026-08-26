from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar


TraceSink = Callable[[str], None]

_TRACE_SINK: ContextVar[TraceSink | None] = ContextVar("action_trace_sink", default=None)
_TRACE_STARTED_AT: ContextVar[float | None] = ContextVar(
    "action_trace_started_at",
    default=None,
)


def trace(message: str) -> None:
    """Emit one trace line when an action trace is active."""
    sink = _TRACE_SINK.get()
    if sink is None:
        return

    started_at = _TRACE_STARTED_AT.get()
    elapsed = 0.0 if started_at is None else time.perf_counter() - started_at
    sink(f"{elapsed:6.2f}s  {message}")


@contextmanager
def capture_action_trace(sink: TraceSink) -> Iterator[None]:
    """Route trace lines from the current worker context to ``sink``."""
    sink_token = _TRACE_SINK.set(sink)
    started_token = _TRACE_STARTED_AT.set(time.perf_counter())
    try:
        yield
    finally:
        _TRACE_STARTED_AT.reset(started_token)
        _TRACE_SINK.reset(sink_token)


__all__ = ["capture_action_trace", "trace"]
