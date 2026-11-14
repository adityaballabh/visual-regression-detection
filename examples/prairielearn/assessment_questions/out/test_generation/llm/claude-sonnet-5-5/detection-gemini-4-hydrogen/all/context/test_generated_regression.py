import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROW_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1) "
    "> main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) "
    "> div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
)

# Question rows that show the point values, with the padding-right they have in the correct page
QUESTION_ROWS = [
    (ROW_PREFIX + " > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)", "24px"),
    (ROW_PREFIX + " > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)", "24px"),
    (ROW_PREFIX + " > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)", "24px"),
    (ROW_PREFIX + " > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)", "24px"),
]


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element is missing from the snapshot")

    def test_question_rows_keep_right_padding(self):
        """Guards the question rows keeping 24px of right padding so the point values
        are not flush against the viewport edge. Broken by the change that removed
        `padding-right:1.5rem` from the tree-row inline style of the question rows.
        """
        for selector, expected in QUESTION_ROWS:
            row = self.find(selector)
            actual = row.styles.get("padding-right")
            self.assertEqual(
                actual,
                expected,
                f"{selector}: padding-right expected {expected} but was {actual}",
            )


if __name__ == "__main__":
    unittest.main()
