import unittest

import cv2
import numpy as np

from image_diff.model import Box
from image_diff.pipeline import diff_images, pad_to_match

_HEIGHT, _WIDTH = 400, 600
_BUTTON = Box(100, 80, 220, 120)
_BEFORE_FILL_COLOR = (255, 0, 0)
_AFTER_FILL_COLOR = (0, 255, 0)
_BEFORE_HEADING_COLOR = (0, 0, 0)
_AFTER_HEADING_COLOR = (0, 0, 255)


def _page(
    fill_color: tuple[int, int, int] = _BEFORE_FILL_COLOR, heading_color: tuple[int, int, int] = _BEFORE_HEADING_COLOR
) -> np.ndarray:
    page = np.full((_HEIGHT, _WIDTH, 3), 255, dtype=np.uint8)
    cv2.putText(page, "Settings", (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, heading_color, 2)
    cv2.rectangle(page, (_BUTTON.x1, _BUTTON.y1), (_BUTTON.x2, _BUTTON.y2), fill_color, cv2.FILLED)
    (text_width, text_height), _ = cv2.getTextSize("Save", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = (_BUTTON.x1 + _BUTTON.x2 - text_width) // 2
    y = (_BUTTON.y1 + _BUTTON.y2 + text_height) // 2
    cv2.putText(page, "Save", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return page


class DiffImagesTests(unittest.TestCase):
    def test_one_pixel_shift_ignored(self):
        before = _page()
        self.assertEqual(diff_images(before, np.roll(before, 1, axis=1)), ())

    def test_fill_change_flags_button(self):
        boxes = diff_images(_page(), _page(fill_color=_AFTER_FILL_COLOR))
        self.assertEqual(len(boxes), 1)
        self.assertEqual(boxes[0].union(_BUTTON), boxes[0])

    def test_numbering_order(self):
        boxes = diff_images(_page(), _page(fill_color=_AFTER_FILL_COLOR, heading_color=_AFTER_HEADING_COLOR))
        self.assertEqual(len(boxes), 2)
        self.assertLess(boxes[0].y2, _BUTTON.y1)

    def test_height_padded(self):
        after = np.vstack([_page(), np.full((50, _WIDTH, 3), 255, dtype=np.uint8)])
        self.assertEqual(diff_images(*pad_to_match(_page(), after)), ())

    def test_width_padded(self):
        after = np.hstack([_page(), np.full((_HEIGHT, 60, 3), 255, dtype=np.uint8)])
        self.assertEqual(diff_images(*pad_to_match(_page(), after)), ())


if __name__ == "__main__":
    unittest.main()
