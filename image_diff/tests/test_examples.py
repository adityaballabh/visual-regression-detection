import unittest
from pathlib import Path

import cv2

from image_diff.dom.parse import load_snapshot
from image_diff.pipeline import diff_images, pad_to_match

_EXAMPLES = Path(__file__).parents[1] / "examples"


class ExampleTests(unittest.TestCase):
    def test_button_darkened_explained(self):
        folder = _EXAMPLES / "button_darkened"
        before, after = pad_to_match(cv2.imread(str(folder / "before.png")), cv2.imread(str(folder / "after.png")))
        snapshots = load_snapshot(folder / "before_snapshot.json"), load_snapshot(folder / "after_snapshot.json")

        changes = diff_images(before, after, snapshots)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].element, "<button> 'Join Now'")
        self.assertEqual(changes[0].detail, "background-color rgb(107, 114, 128) -> rgb(75, 85, 99)")


if __name__ == "__main__":
    unittest.main()
