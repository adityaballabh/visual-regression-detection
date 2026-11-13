import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROW_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1) > "
    "main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > "
    "div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > "
)
# Question rows for Partial credit 1 to 4, from the flagged boxes
QUESTION_ROW_SELECTORS = [
    ROW_PREFIX + "div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]
# Padding right of every flagged row in the before snapshot
EXPECTED_PADDING_RIGHT = "24px"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_rows_keep_right_padding(self):
        """Guards the question rows keeping their 24px right padding so the points badge stays off the
        right edge, broken when TreeQuestionRow.tsx commented out `paddingRight: '1.5rem'`."""
        elements_by_selector = {}
        for element in self.snapshot.elements:
            if not element.frames:
                elements_by_selector[element.selector] = element
        for selector in QUESTION_ROW_SELECTORS:
            with self.subTest(selector=selector):
                self.assertIn(selector, elements_by_selector, f"{selector}: question row is missing")
                actual = elements_by_selector[selector].styles.get("padding-right")
                self.assertEqual(
                    actual,
                    EXPECTED_PADDING_RIGHT,
                    f"{selector}: padding-right expected {EXPECTED_PADDING_RIGHT}, got {actual}",
                )


if __name__ == "__main__":
    unittest.main()
