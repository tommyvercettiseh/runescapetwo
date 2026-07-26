import cv2
import numpy as np

from core.vision.colour_detection import (
    blobs_from_mask,
    build_colour_mask,
    normalize_colour_name,
)


def test_dutch_colour_aliases_are_supported():
    assert normalize_colour_name("paars") == "purple"
    assert normalize_colour_name("cyaan") == "cyan"


def test_build_colour_mask_detects_green_pixels():
    image = np.zeros((20, 20, 3), dtype=np.uint8)
    image[5:15, 5:15] = (0, 255, 0)
    mask = build_colour_mask(image, "green")
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


def test_small_noise_is_filtered_out():
    mask = np.zeros((20, 20), dtype=np.uint8)
    mask[2, 2] = 255
    assert blobs_from_mask(mask, minimum_area_px=5) == []
