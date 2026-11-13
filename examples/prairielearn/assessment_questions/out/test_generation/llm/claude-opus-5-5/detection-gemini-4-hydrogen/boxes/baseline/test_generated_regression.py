import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROWS_SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1)"
    " > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1)"
    " > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
)
# The four "Partial credit" question rows flagged by the detector
QUESTION_ROW_SELECTORS = [
    ROWS_SELECTOR + " > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    ROWS_SELECTOR + " > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    ROWS_SELECTOR + " > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    ROWS_SELECTOR + " > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]
# Right padding of each row in the before snapshot
EXPECTED_PADDING_RIGHT = "24px"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_rows_keep_right_padding(self):
        """Guards the 24px right padding on the 'Partial credit' question rows, lost when
        TreeQuestionRow.tsx commented out `paddingRight: '1.5rem'` in the row's inline style."""
        elements_by_selector = {}
        for element in self.snapshot.elements:
            if not element.frames:
                elements_by_selector[element.selector] = element
        for selector in QUESTION_ROW_SELECTORS:
            with self.subTest(selector=selector):
                row = elements_by_selector.get(selector)
                self.assertIsNotNone(row, f"{selector}: question row is missing")
                actual = row.styles.get("padding-right")
                self.assertEqual(
                    actual,
                    EXPECTED_PADDING_RIGHT,
                    f"{selector}: padding-right expected {EXPECTED_PADDING_RIGHT}, got {actual}",
                )


if __name__ == "__main__":
    unittest.main()
