import unittest
from pathlib import Path

import cv2

from image_diff.dom.parse import load_snapshot
from image_diff.model import Change
from image_diff.pipeline import diff_images, pad_to_match

_EXAMPLES = Path(__file__).parents[2] / "examples" / "general"


def _changes(example: str) -> tuple[Change, ...]:
    captures = _EXAMPLES / example / "captures"
    before, after = pad_to_match(cv2.imread(str(captures / "before.png")), cv2.imread(str(captures / "after.png")))
    snapshots = load_snapshot(captures / "before_snapshot.json"), load_snapshot(captures / "after_snapshot.json")
    return diff_images(before, after, snapshots)


class ExampleTests(unittest.TestCase):
    def test_examples_explained(self):
        expected = {
            "button_enlarged": [
                (
                    "<button> 'Learn More'",
                    (
                        "padding-bottom 8px -> 12px; padding-left 16px -> 24px; padding-right 16px -> 24px; "
                        "padding-top 8px -> 12px; width 120px -> 136px; height 40px -> 48px. content moved 8px down"
                    ),
                ),
            ],
            "synthetic_color_and_move": [
                (
                    "<button> 'Open an Account'",
                    (
                        "background-color rgb(37, 99, 235) -> rgb(220, 38, 38); padding-bottom 12px -> 24px; "
                        "padding-top 12px -> 24px; height 42px -> 66px. content moved 24px down"
                    ),
                ),
            ],
            "synthetic_five_changes": [
                ("<a> 'About'", "removed. content moved 66px right"),
                (
                    "<h1> 'Welcome to Banking Institution'",
                    "font-size 40px -> 56px; height 46px -> 64px. content moved 18px down",
                ),
                ("<div> containing 'Savings Accounts'", "background-color rgb(220, 252, 231) -> rgb(254, 202, 202)"),
                (
                    "<footer> '© 2022 Banking Institution. All rights r...'",
                    "padding-bottom 24px -> 48px; padding-top 24px -> 48px; height 66px -> 114px",
                ),
                ("<li> 'Personal finance coaching'", "added. content moved 18px down"),
            ],
            "heading_centered": [
                ("<section> containing 'Welcome to our Agriculture Company'", "text-align start -> center")
            ],
        }
        for example, rows in expected.items():
            with self.subTest(example):
                changes = _changes(example)
                self.assertEqual([(change.element, change.detail) for change in changes], rows)


if __name__ == "__main__":
    unittest.main()
