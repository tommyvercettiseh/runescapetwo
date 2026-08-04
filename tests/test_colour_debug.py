import numpy as np

from tools.vision_tester.colour_debug import (
    dominant_colours,
    editor_sample_from_ranges,
    isolate_colour,
)


def test_isolate_colour_keeps_only_masked_pixels() -> None:
    image = np.array(
        [
            [[255, 0, 0], [0, 255, 0]],
            [[0, 0, 255], [255, 255, 255]],
        ],
        dtype=np.uint8,
    )
    mask = np.array([[255, 0], [0, 255]], dtype=np.uint8)

    isolated = isolate_colour(image, mask)

    assert isolated.tolist() == [
        [[255, 0, 0], [0, 0, 0]],
        [[0, 0, 0], [255, 255, 255]],
    ]


def test_dominant_colours_reports_pixel_counts_and_percentages() -> None:
    image = np.zeros((10, 10, 3), dtype=np.uint8)
    image[:7] = (255, 0, 0)
    image[7:] = (0, 0, 255)

    colours = dominant_colours(image, limit=5)

    assert len(colours) == 2
    assert colours[0].pixels == 70
    assert colours[0].percentage == 70.0
    assert colours[1].pixels == 30
    assert colours[1].percentage == 30.0


def test_dominant_colours_respects_limit() -> None:
    image = np.array(
        [[[255, 0, 0], [0, 255, 0], [0, 0, 255]]],
        dtype=np.uint8,
    )

    assert len(dominant_colours(image, limit=2)) == 2


def test_editor_sample_uses_centre_of_regular_range() -> None:
    assert editor_sample_from_ranges((((140, 180, 160), (150, 240, 220)),)) == (
        145,
        210,
        190,
    )


def test_editor_sample_understands_wrapped_red_range() -> None:
    ranges = (
        ((173, 230, 230), (179, 250, 250)),
        ((0, 230, 230), (3, 250, 250)),
    )

    assert editor_sample_from_ranges(ranges) == (178, 240, 240)
