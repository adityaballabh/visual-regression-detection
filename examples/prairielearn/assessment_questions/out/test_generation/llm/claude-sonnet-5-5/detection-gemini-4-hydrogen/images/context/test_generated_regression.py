import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROW_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > "
    "div:nth-child(1) > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > "
    "div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > "
    "div:nth-child(2) > div:nth-child(1) > "
)

ROW_SELECTORS = {
    "Partial credit 1": ROW_PREFIX + "div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    "Partial credit 2": ROW_PREFIX + "div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    "Partial credit 3": ROW_PREFIX + "div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    "Partial credit 4": ROW_PREFIX + "div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
}

EXPECTED_PADDING_RIGHT = "24px"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_row(self, selector):
        for element in self.snapshot.elements:
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_question_rows_keep_right_padding(self):
        """Guards the question rows in the assessment questions tree keeping 24px right padding.

        The change that broke it comments out `paddingRight: '1.5rem'` in TreeQuestionRow.tsx,
        which pushes the badge and points values flush against the right edge and clips the last digit.
        """
        for name, selector in ROW_SELECTORS.items():
            with self.subTest(row=name):
                row = self.find_row(selector)
                actual = row.styles.get("padding-right")
                self.assertEqual(
                    actual,
                    EXPECTED_PADDING_RIGHT,
                    f"{selector}: padding-right expected {EXPECTED_PADDING_RIGHT}, got {actual}",
                )


if __name__ == "__main__":
    unittest.main()
