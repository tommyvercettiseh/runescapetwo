import cv2
import numpy as np

from core.vision.colour_detection import (
    blobs_from_mask,
    build_mask_from_ranges,
)


def test_build_mask_from_ranges_detects_green_pixels():
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:15, 5:15] = (0, 255, 0)
    mask = build_mask_from_ranges(
        image,
        (((35, 200, 200), (85, 255, 255)),),
    )
    assert int(mask[10, 10]) == 255
    assert int(mask[0, 0]) == 0


def test_blobs_are_returned_in_absolute_screen_coordinates():
    mask = np.zeros((40, 40), dtype=np.uint8)
    cv2.rectangle(mask, (5, 8), (20, 25), 255, thickness=-1)

    blobs = blobs_from_mask(mask, origin=(958, 498), minimum_area_px=10)

    assert len(blobs) == 1
    blob = blobs[0]
    assert blob.x == 963
    assert blob.y == 506
    assert blob.centroid_x >= 963
    assert blob.centroid_y >= 506
    assert blob.area_px == 288


def test_small_noise_is_filtered_out():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2, 2] = 255
    assert blobs_from_mask(mask, minimum_area_px=5) == []
