from __future__ import annotations

import pytest

from core.movements import create_path


def test_linear_path_reaches_exact_target() -> None:
    path = create_path("linear", (10, 20), (110, 220), 10)

    assert len(path) == 10
    assert path[-1] == (110, 220)


def test_unknown_movement_fails_clearly() -> None:
    with pytest.raises(ValueError, match="Unknown movement"):
        create_path("missing", (0, 0), (10, 10), 5)
