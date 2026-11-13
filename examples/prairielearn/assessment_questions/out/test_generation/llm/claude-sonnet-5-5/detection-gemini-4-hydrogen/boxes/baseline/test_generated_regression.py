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

# Selector suffix of each flagged 'Partial credit' row, with the padding-right it had before the change
PARTIAL_CREDIT_ROWS = {
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

    def find(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"Element not found: {selector}")

    def test_partial_credit_rows_keep_right_padding(self):
        """Guards the question rows that lost their right padding (padding-right 24px -> 0px).

        The change dropped `paddingRight: '1.5rem'` from the inline style of the question
        tree rows, so the 'Partial credit' rows sit flush against the right edge.
        """
        for label, selector in PARTIAL_CREDIT_ROWS.items():
            element = self.find(selector)
            actual = element.styles.get("padding-right")
            self.assertEqual(
                actual,
                EXPECTED_PADDING_RIGHT,
                f"{label} row {selector}: property padding-right expected {EXPECTED_PADDING_RIGHT} but was {actual}",
            )


if __name__ == "__main__":
    unittest.main()
