from contextlib import nullcontext

from core.vision.models import Hit


def _hit(x: int) -> Hit:
    return Hit(
        x=x,
        y=20,
        width=10,
        height=10,
        shape_score=0.99,
        color_score=0.99,
        method="TM_CCOEFF_NORMED",
    )


def test_random_target_image_chooses_from_all_hits(monkeypatch) -> None:
    from core import mouse_actions

    hits = [_hit(10), _hit(30), _hit(50)]
    selected = hits[2]

    monkeypatch.setattr(
        mouse_actions,
        "find_all_images",
        lambda *_args, **_kwargs: hits,
    )
    monkeypatch.setattr(mouse_actions.random, "choice", lambda values: values[2])

    result = mouse_actions._find_random_target_image(
        "Item",
        area_name="Inventory_Area",
        bot_id=1,
    )

    assert result is selected


def test_click_image_uses_random_target(monkeypatch) -> None:
    from core import mouse_actions

    selected = _hit(50)
    moved_to: list[tuple[int, int, int, int]] = []

    monkeypatch.setattr(
        mouse_actions,
        "_find_random_target_image",
        lambda *_args, **_kwargs: selected,
    )
    monkeypatch.setattr(mouse_actions.mouse, "action_guard", nullcontext)
    monkeypatch.setattr(
        mouse_actions.mouse,
        "move_and_click_target",
        lambda left, top, right, bottom, **_kwargs: moved_to.append(
            (left, top, right, bottom)
        ),
    )
    monkeypatch.setattr(
        mouse_actions,
        "_success",
        lambda *args, **kwargs: mouse_actions.MouseActionResult(
            success=True,
            action="click_image",
            message="ok",
            bounds=kwargs.get("bounds"),
        ),
    )

    result = mouse_actions.click_image(
        "Item",
        area_name="Inventory_Area",
        image_edge_padding=0,
        require_external_mouse=False,
    )

    assert result.success is True
    assert moved_to == [(50, 20, 60, 30)]
