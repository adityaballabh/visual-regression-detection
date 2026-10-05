import json
import tempfile
import unittest
from pathlib import Path

import cv2
import numpy as np

from image_diff.model import Box, Change, Kind
from image_diff.output import write

_BUTTON = Box(120, 96, 248, 136)
_RESTYLED_BUTTON = Change(
    _BUTTON,
    _BUTTON,
    Kind.COLOR_AND_SHAPE,
    element="<button> 'Save'",
    selector="html:nth-child(1) > body:nth-child(2) > button:nth-child(1)",
    frames=(),
    detail="background-color rgb(107, 114, 128) -> rgb(37, 99, 235); font-size 16px -> 20px",
)

_PIXEL_ONLY_REMOVAL = Change(Box(16, 400, 320, 440), None, Kind.SHAPE)


class OutputTests(unittest.TestCase):
    def setUp(self):
        self.page = np.full((480, 640, 3), 255, np.uint8)
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        self.out = Path(folder.name)
        write(self.out, self.page, self.page, (_RESTYLED_BUTTON, _PIXEL_ONLY_REMOVAL))

    def test_rows_show_element_or_null(self):
        rows = json.loads((self.out / "boxes.json").read_text())

        self.assertEqual(rows[0]["type"], "color_and_shape")
        self.assertEqual(rows[0]["element"], "<button> 'Save'")
        self.assertEqual(rows[0]["frames"], [])
        self.assertEqual([None] * 4, [rows[1][key] for key in ("element", "selector", "frames", "detail")])

    def test_color_and_shape_drawn_on_both_pairs(self):
        for name in ("after_color.png", "after_shape.png"):
            image = cv2.imread(str(self.out / name))
            self.assertFalse(np.array_equal(image, self.page), name)


if __name__ == "__main__":
    unittest.main()
