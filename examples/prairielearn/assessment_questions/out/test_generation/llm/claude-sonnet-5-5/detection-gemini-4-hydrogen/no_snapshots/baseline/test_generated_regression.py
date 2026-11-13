import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

EXPECTED_PADDING_RIGHT = "24px"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_rows_keep_right_padding(self):
        """Guards the question rows' right padding in TreeQuestionRow.tsx.

        Commenting out `paddingRight: '1.5rem'` removed the 24px right padding, which shifted
        the tag badges and point values 24px right and clipped them at the viewport edge.
        """
        rows = [
            element
            for element in self.snapshot.elements
            if "tree-row" in element.attributes.get("class", "").split() and element.attributes.get("role") == "button"
        ]
        self.assertGreaterEqual(len(rows), 4, "Expected at least four question rows (div.tree-row)")
        for row in rows:
            actual = row.styles["padding-right"]
            self.assertEqual(
                actual,
                EXPECTED_PADDING_RIGHT,
                f"{row.selector}: padding-right expected {EXPECTED_PADDING_RIGHT}, got {actual}",
            )
