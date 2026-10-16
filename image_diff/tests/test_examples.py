import unittest
from pathlib import Path

import cv2

from image_diff.dom.parse import load_snapshot
from image_diff.model import Change
from image_diff.pipeline import diff_images, pad_to_match

_EXAMPLES = Path(__file__).parents[1] / "examples"


def _changes(example: str) -> tuple[Change, ...]:
    folder = _EXAMPLES / example
    before, after = pad_to_match(cv2.imread(str(folder / "before.png")), cv2.imread(str(folder / "after.png")))
    snapshots = load_snapshot(folder / "before_snapshot.json"), load_snapshot(folder / "after_snapshot.json")
    return diff_images(before, after, snapshots)


class ExampleTests(unittest.TestCase):
    def test_examples_one_explained_change_each(self):
        expected = {
            "button_darkened": ("<button> 'Join Now'", "background-color rgb(107, 114, 128) -> rgb(75, 85, 99)"),
            "button_enlarged": (
                "<button> 'Learn More'",
                (
                    "padding-bottom 8px -> 12px; padding-left 16px -> 24px; padding-right 16px -> 24px; "
                    "padding-top 8px -> 12px; width 120px -> 136px; height 40px -> 48px. content moved 8px down"
                ),
            ),
            "section_added": ("<section> containing 'Featured Collection'", "added. content moved 208px down"),
        }
        for example, (element, detail) in expected.items():
            with self.subTest(example):
                changes = _changes(example)
                self.assertEqual([(change.element, change.detail) for change in changes], [(element, detail)])


if __name__ == "__main__":
    unittest.main()
