import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROWS = "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1) > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"

# Question rows for Partial credit 1 to 4, all 24px of right padding in the before snapshot
QUESTION_ROW_SELECTORS = [
    f"{ROWS} > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    f"{ROWS} > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    f"{ROWS} > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    f"{ROWS} > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_rows_keep_right_padding(self):
        """Guards the 1.5rem right padding on assessment question rows, which keeps the
        tag and points badge off the right edge. Commenting out `paddingRight: '1.5rem'`
        in TreeQuestionRow.tsx dropped it to 0px."""
        elements_by_selector = {}
        for element in self.snapshot.elements:
            if not element.frames:
                elements_by_selector[element.selector] = element
        for selector in QUESTION_ROW_SELECTORS:
            with self.subTest(selector=selector):
                self.assertIn(selector, elements_by_selector, f"{selector}: question row is missing")
                actual = elements_by_selector[selector].styles.get("padding-right")
                self.assertEqual(actual, "24px", f"{selector}: padding-right expected 24px, got {actual}")


if __name__ == "__main__":
    unittest.main()
