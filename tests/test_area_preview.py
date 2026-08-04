from tools.area_maker.preview import PreviewRegion, calculate_crop, calculate_scale


def test_crop_adds_margin_and_stays_inside_desktop() -> None:
    crop = calculate_crop(
        PreviewRegion(x=3, y=4, width=20, height=10),
        desktop_size=(100, 80),
        margin=8,
    )

    assert crop == PreviewRegion(x=0, y=0, width=31, height=22)


def test_crop_handles_bottom_right_edge() -> None:
    crop = calculate_crop(
        PreviewRegion(x=90, y=70, width=10, height=10),
        desktop_size=(100, 80),
        margin=8,
    )

    assert crop == PreviewRegion(x=82, y=62, width=18, height=18)


def test_small_area_gets_integer_nearest_neighbour_zoom() -> None:
    scale = calculate_scale(
        PreviewRegion(x=0, y=0, width=40, height=20),
        preview_size=(380, 260),
    )

    assert scale == 9


def test_large_area_never_scales_below_one() -> None:
    scale = calculate_scale(
        PreviewRegion(x=0, y=0, width=1280, height=720),
        preview_size=(380, 260),
    )

    assert scale == 1
