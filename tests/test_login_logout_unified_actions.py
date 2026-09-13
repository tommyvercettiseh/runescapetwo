from tools.unified_tester.action_registry import action_names


def test_unified_tester_exposes_login_and_logout_actions() -> None:
    names = action_names()
    assert "Login" in names
    assert "Logout" in names
