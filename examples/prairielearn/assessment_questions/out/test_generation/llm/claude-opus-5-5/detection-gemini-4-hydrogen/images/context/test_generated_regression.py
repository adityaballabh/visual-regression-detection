import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

ROW_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1)"
    " > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1)"
    " > div:nth-child(1) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
)
# Question rows for Partial credit 1 to 4, all with 24px right padding in the before snapshot
QUESTION_ROW_SELECTORS = [
    f"{ROW_PREFIX} > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    f"{ROW_PREFIX} > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    f"{ROW_PREFIX} > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    f"{ROW_PREFIX} > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
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
        """Guards the question rows keeping their right padding so the points badge is not clipped.

        Broken by commenting out paddingRight: '1.5rem' in TreeQuestionRow.tsx.
        """
        elements_by_selector = {}
        for element in self.snapshot.elements:
            if not element.frames:
                elements_by_selector[element.selector] = element
        for selector in QUESTION_ROW_SELECTORS:
            with self.subTest(selector=selector):
                row = elements_by_selector.get(selector)
                self.assertIsNotNone(row, f"{selector}: question row missing")
                padding_right = row.styles.get("padding-right")
                self.assertEqual(
                    padding_right,
                    EXPECTED_PADDING_RIGHT,
                    f"{selector}: padding-right expected {EXPECTED_PADDING_RIGHT}, got {padding_right}",
                )
