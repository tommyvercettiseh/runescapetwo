import numpy as np

from tools.vision_tester.colour_debug import (
    dominant_colours,
    editor_sample_from_ranges,
    filter_mask_by_blob_size,
    isolate_colour,
    measure_mask_blobs,
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


def test_filter_mask_by_blob_size_removes_regions_outside_limits() -> None:
    mask = np.zeros((5, 8), dtype=np.uint8)
    mask[0, 0] = 255
    mask[1:3, 2:4] = 255
    mask[1:4, 5:8] = 255

    filtered, count = filter_mask_by_blob_size(
        mask,
        minimum_area_px=3,
        maximum_area_px=5,
    )

    assert count == 1
    assert np.count_nonzero(filtered) == 4


def test_measure_mask_blobs_returns_largest_region_first() -> None:
    mask = np.zeros((8, 10), dtype=np.uint8)
    mask[1:3, 1:4] = 255
    mask[3:7, 5:9] = 255

    blobs = measure_mask_blobs(mask)

    assert [(blob.x, blob.y, blob.width, blob.height, blob.area_px) for blob in blobs] == [
        (5, 3, 4, 4, 16),
        (1, 1, 3, 2, 6),
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
