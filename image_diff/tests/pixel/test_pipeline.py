import unittest

import cv2
import numpy as np

from image_diff.model import Box, Kind
from image_diff.pipeline import diff_images, pad_to_match

_HEIGHT, _WIDTH = 400, 600
_BUTTON = Box(100, 80, 220, 120)
_BEFORE_FILL_COLOR = (255, 0, 0)
_AFTER_FILL_COLOR = (0, 255, 0)
_BEFORE_HEADING_COLOR = (0, 0, 0)
_AFTER_HEADING_COLOR = (0, 0, 255)


def _page(
    fill_color: tuple[int, int, int] = _BEFORE_FILL_COLOR,
    heading_color: tuple[int, int, int] = _BEFORE_HEADING_COLOR,
    heading_text: str = "Settings",
    button: Box = _BUTTON,
) -> np.ndarray:
    page = np.full((_HEIGHT, _WIDTH, 3), 255, dtype=np.uint8)
    cv2.putText(page, heading_text, (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8, heading_color, 2)
    cv2.rectangle(page, (button.x1, button.y1), (button.x2, button.y2), fill_color, cv2.FILLED)
    (text_width, text_height), _ = cv2.getTextSize("Save", cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2)
    x = (button.x1 + button.x2 - text_width) // 2
    y = (button.y1 + button.y2 + text_height) // 2
    cv2.putText(page, "Save", (x, y), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
    return page


class DiffImagesTests(unittest.TestCase):
    def test_one_pixel_shift_ignored(self):
        before = _page()
        self.assertEqual(diff_images(before, np.roll(before, 1, axis=1)), ())

    def test_fill_change_flags_button(self):
        changes = diff_images(_page(), _page(fill_color=_AFTER_FILL_COLOR))
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, Kind.COLOR)
        self.assertEqual(changes[0].after.union(_BUTTON), changes[0].after)

    def test_replaced_text_flagged_as_shape(self):
        changes = diff_images(_page(), _page(heading_text="Profile"))
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, Kind.SHAPE)

    def test_widened_button_fitted_per_side(self):
        changes = diff_images(_page(), _page(button=Box(100, 80, 300, 120)))
        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, Kind.SHAPE)
        self.assertLess(changes[0].before.x2, changes[0].after.x2)

    def test_numbering_order(self):
        changes = diff_images(_page(), _page(fill_color=_AFTER_FILL_COLOR, heading_color=_AFTER_HEADING_COLOR))
        self.assertEqual(len(changes), 2)
        self.assertLess(changes[0].before.y2, _BUTTON.y1)

    def test_smaller_image_padded(self):
        taller = np.vstack([_page(), np.full((50, _WIDTH, 3), 255, dtype=np.uint8)])
        wider = np.hstack([_page(), np.full((_HEIGHT, 60, 3), 255, dtype=np.uint8)])

        self.assertEqual(diff_images(*pad_to_match(_page(), taller)), ())
        self.assertEqual(diff_images(*pad_to_match(_page(), wider)), ())


if __name__ == "__main__":
    unittest.main()
