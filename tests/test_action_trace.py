from core.action_trace import capture_action_trace, trace


def test_action_trace_is_silent_without_capture() -> None:
    trace("[TEST] ignored")


def test_action_trace_routes_timestamped_lines_to_active_sink() -> None:
    lines: list[str] = []

    with capture_action_trace(lines.append):
        trace("[CHECK] hello")
        trace("[OK] done")

    assert len(lines) == 2
    assert lines[0].endswith("[CHECK] hello")
    assert lines[1].endswith("[OK] done")
    assert lines[0].split("s", 1)[0].strip()
