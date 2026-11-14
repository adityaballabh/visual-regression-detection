import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Right padding of each question row in the before snapshot, 1.5rem
ROW_PADDING_RIGHT = "24px"
# Gap between the tags and points and the row's right edge, the same 24px padding
ROW_INSET = 24


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_question_row_trailing_content_stays_inset(self):
        """Guards the 24px right shift of the question tags and points in the assessment questions tree.

        TreeQuestionRow.tsx commented out the row's `paddingRight: '1.5rem'`, so the tags and
        points slid to the viewport edge and the last digit got clipped.
        """
        question_rows = []
        for element in self.snapshot.elements:
            classes = element.attributes.get("class", "").split()
            if "tree-row" in classes and element.attributes.get("role") == "button":
                question_rows.append(element)
        self.assertTrue(question_rows, "No question rows (div.tree-row[role=button]) found")

        for row in question_rows:
            actual = row.styles["padding-right"]
            self.assertEqual(
                actual,
                ROW_PADDING_RIGHT,
                f"{row.selector} padding-right: expected {ROW_PADDING_RIGHT}, got {actual}",
            )
            # The tags and points are the row's rightmost child
            content_right = max(child.box.x2 for child in self.snapshot.elements if child.parent == row.id)
            inset = row.box.x2 - content_right
            self.assertGreaterEqual(
                inset,
                ROW_INSET - 1,
                f"{row.selector} trailing content inset: expected {ROW_INSET}px, got {inset}px",
            )


if __name__ == "__main__":
    unittest.main()
