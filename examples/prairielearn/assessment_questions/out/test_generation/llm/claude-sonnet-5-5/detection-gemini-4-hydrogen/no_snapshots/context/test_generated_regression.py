import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

EXPECTED_PADDING_RIGHT = 24
TOLERANCE = 1


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))
        cls.by_id = {element.id: element for element in cls.snapshot.elements}

    def question_row(self, badge):
        # Walk up to the tree row that holds the badge
        element = self.by_id.get(badge.parent)
        while element is not None:
            if "tree-row" in element.attributes.get("class", "").split():
                return element
            element = self.by_id.get(element.parent)
        return None

    def is_inside(self, element, row):
        parent = self.by_id.get(element.parent)
        while parent is not None:
            if parent.id == row.id:
                return True
            parent = self.by_id.get(parent.parent)
        return False

    def test_question_rows_keep_right_padding(self):
        """Guards the question rows in the assessment questions tree keeping their 1.5rem right padding.

        The regression came from commenting out `paddingRight: '1.5rem'` in TreeQuestionRow.tsx, which shifted
        the topic badges and point values 24 px right so the points text clipped at the viewport edge.
        """
        badges = [e for e in self.snapshot.elements if e.visible and e.own_text == "Algebra"]
        self.assertGreaterEqual(len(badges), 4, f"Expected at least 4 'Algebra' badges, found {len(badges)}")

        for badge in badges:
            row = self.question_row(badge)
            self.assertIsNotNone(row, f"{badge.selector}: no clickable question row found above the badge")

            padding = float(row.styles["padding-right"].removesuffix("px"))
            self.assertAlmostEqual(
                padding,
                EXPECTED_PADDING_RIGHT,
                delta=TOLERANCE,
                msg=f"{row.selector}: padding-right expected {EXPECTED_PADDING_RIGHT}px, actual {padding}px",
            )

            # Row content, including the points text, must end before the right padding
            limit = row.box.x2 - EXPECTED_PADDING_RIGHT
            for element in self.snapshot.elements:
                if element.visible and element.own_text and self.is_inside(element, row):
                    self.assertLessEqual(
                        element.box.x2,
                        limit + TOLERANCE,
                        f"{element.selector}: right edge expected <= {limit}, actual {element.box.x2}",
                    )


if __name__ == "__main__":
    unittest.main()
