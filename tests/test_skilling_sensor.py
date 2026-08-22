import cv2
import numpy as np

from core.sensors.skilling_sensor import classify_skilling_frame


def _solid_hsv(hue: int, saturation: int = 255, value: int = 255) -> np.ndarray:
    hsv = np.zeros((4, 4, 3), dtype=np.uint8)
    hsv[:, :, 0] = hue
    hsv[:, :, 1] = saturation
    hsv[:, :, 2] = value
    return cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)


def test_green_means_skilling():
    reading = classify_skilling_frame(_solid_hsv(60))
    assert reading.skilling is True
    assert reading.green_pixels > 0
    assert reading.red_pixels == 0


def test_red_means_not_skilling():
    reading = classify_skilling_frame(_solid_hsv(0))
    assert reading.skilling is False
    assert reading.red_pixels > 0


def test_no_red_or_green_means_not_skilling():
    frame = np.zeros((4, 4, 3), dtype=np.uint8)
    reading = classify_skilling_frame(frame)
    assert reading.skilling is False
    assert reading.green_pixels == 0
    assert reading.red_pixels == 0


def test_red_takes_priority_over_green():
    frame = np.zeros((2, 2, 3), dtype=np.uint8)
    hsv = np.zeros((2, 2, 3), dtype=np.uint8)
    hsv[:, :, 1] = 255
    hsv[:, :, 2] = 255
    hsv[0, :, 0] = 60
    hsv[1, :, 0] = 0
    frame = cv2.cvtColor(hsv, cv2.COLOR_HSV2RGB)

    reading = classify_skilling_frame(frame)
    assert reading.green_pixels > 0
    assert reading.red_pixels > 0
    assert reading.skilling is False
