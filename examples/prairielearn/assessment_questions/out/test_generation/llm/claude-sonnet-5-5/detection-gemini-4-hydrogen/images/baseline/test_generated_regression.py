import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROW_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > "
    "div:nth-child(1) > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > "
    "div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > "
    "div:nth-child(2) > div:nth-child(1)"
)
ROW_SELECTORS = [
    ROW_PREFIX + " > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + " > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    ROW_PREFIX + " > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    ROW_PREFIX + " > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]
EXPECTED_PADDING_RIGHT = "24px"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_rows_keep_right_padding(self):
        """Guards the right padding of the question tree rows.

        Commenting out `paddingRight: '1.5rem'` in TreeQuestionRow.tsx removed the row's
        right padding, so the Algebra badge and point values shifted to the viewport edge.
        """
        for selector in ROW_SELECTORS:
            matches = [e for e in self.snapshot.elements if e.selector == selector and not e.frames]
            self.assertEqual(len(matches), 1, f"{selector}: expected one element, found {len(matches)}")
            actual = matches[0].styles.get("padding-right")
            self.assertEqual(
                actual,
                EXPECTED_PADDING_RIGHT,
                f"{selector}: property padding-right expected {EXPECTED_PADDING_RIGHT}, actual {actual}",
            )


if __name__ == "__main__":
    unittest.main()
