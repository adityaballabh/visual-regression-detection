import unittest
from pathlib import Path

import cv2

from image_diff.dom.parse import load_snapshot
from image_diff.model import Change
from image_diff.pipeline import diff_images, pad_to_match

_EXAMPLES = Path(__file__).parents[1] / "examples"


def _changes(example: str) -> tuple[Change, ...]:
    inputs = _EXAMPLES / example / "input"
    before, after = pad_to_match(cv2.imread(str(inputs / "before.png")), cv2.imread(str(inputs / "after.png")))
    snapshots = load_snapshot(inputs / "before_snapshot.json"), load_snapshot(inputs / "after_snapshot.json")
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
            "button_removed": [("<button> 'Get Involved'", "removed. content moved 40px up")],
            "synthetic_color_and_move": [
                (
                    "<button> 'Get Started'",
                    (
                        "background-color rgb(37, 99, 235) -> rgb(220, 38, 38); padding-bottom 12px -> 24px; "
                        "padding-top 12px -> 24px; height 42px -> 66px. content moved 24px down"
                    ),
                ),
            ],
            "synthetic_five_changes": [
                ("<a> 'About'", "removed. content moved 66px right"),
                (
                    "<h1> 'Welcome to Acme Studio'",
                    "font-size 40px -> 56px; height 46px -> 64px. content moved 18px down",
                ),
                ("<div> containing 'Build'", "background-color rgb(220, 252, 231) -> rgb(254, 202, 202)"),
                (
                    "<footer> '© 2026 Acme Studio'",
                    "padding-bottom 24px -> 48px; padding-top 24px -> 48px; height 66px -> 114px",
                ),
                ("<li> 'Tested'", "added. content moved 36px down"),
            ],
            "heading_centered": [
                ("<section> containing 'Welcome to our Agriculture Company'", "text-align start -> center")
            ],
            "section_added": [("<section> containing 'Featured Collection'", "added. content moved 208px down")],
        }
        for example, rows in expected.items():
            with self.subTest(example):
                changes = _changes(example)
                self.assertEqual([(change.element, change.detail) for change in changes], rows)


if __name__ == "__main__":
    unittest.main()
