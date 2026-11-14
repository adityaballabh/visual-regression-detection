import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Before snapshot: top of the cards section
CARDS_TOP = 269
# Before snapshot: top of the 'Our Services' section
FEATURES_TOP = 414


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, tag, element_id):
        for element in self.snapshot.elements:
            if element.frames == () and element.tag == tag and element.attributes.get("id") == element_id:
                return element
        self.fail(f"No <{tag}> with id {element_id!r} in the snapshot")

    def assert_top(self, element, expected):
        self.assertLessEqual(
            abs(element.box.y1 - expected),
            1,
            f"{element.selector} top is {element.box.y1}px, expected {expected}px",
        )

    def test_sections_stay_in_place(self):
        """Guards the cards and 'Our Services' sections shifting down below the hero.

        The 'Open an Account' button's padding went from 12px to 24px, which pushed both sections down 24px.
        """
        self.assert_top(self.find("section", "cards"), CARDS_TOP)
        self.assert_top(self.find("section", "features"), FEATURES_TOP)
