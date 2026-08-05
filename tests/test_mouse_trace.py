from tools.vision_tester.mouse_trace import fading_trace_colour


def test_fading_trace_becomes_brighter_for_recent_points() -> None:
    assert fading_trace_colour(0.0) == "#12180c"
    assert fading_trace_colour(1.0) == "#8ec63f"
    assert fading_trace_colour(-10) == fading_trace_colour(0)
    assert fading_trace_colour(10) == fading_trace_colour(1)
