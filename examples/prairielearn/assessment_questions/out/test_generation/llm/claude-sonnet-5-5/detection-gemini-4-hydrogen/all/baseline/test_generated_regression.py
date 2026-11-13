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

ROW_SELECTORS = [
    ROW_PREFIX + "div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    ROW_PREFIX + "div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]

EXPECTED_PADDING_RIGHT = "24px"


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
        self.fail(f"{selector}: element not found in snapshot")

    def test_question_rows_keep_right_padding(self):
        """Guards the 24px right padding on the question rows of the assessment questions tree.

        The regression came from TreeQuestionRow.tsx, where the `paddingRight: '1.5rem'`
        style (reserving room for macOS overlay scrollbars) was commented out.
        """
        for selector in ROW_SELECTORS:
            row = self.find(selector)
            actual = row.styles.get("padding-right")
            self.assertEqual(
                actual,
                EXPECTED_PADDING_RIGHT,
                f"{selector}: property padding-right expected {EXPECTED_PADDING_RIGHT!r}, actual {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
