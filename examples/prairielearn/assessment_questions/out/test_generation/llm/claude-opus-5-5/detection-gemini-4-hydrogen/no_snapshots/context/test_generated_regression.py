import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

TREE = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > div:nth-child(1) > main:nth-child(3)"
    " > div:nth-child(3) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1)"
    " > div:nth-child(2) > div:nth-child(1)"
)
# Question row selector, topic badge left edge, points text right edge, all from the before snapshot
QUESTION_ROWS = [
    (f"{TREE} > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)", "10, 5, 1", 1087, 1256),
    (f"{TREE} > div:nth-child(2) > div:nth-child(2) > div:nth-child(1)", "10, 5, 1", 1087, 1256),
    (f"{TREE} > div:nth-child(2) > div:nth-child(3) > div:nth-child(1)", "15, 10, 5, 1", 1087, 1256),
    (f"{TREE} > div:nth-child(2) > div:nth-child(4) > div:nth-child(1)", "20, 15, 10, 5, 1", 1066, 1256),
]


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def descendants(self, row):
        ids = {row.id}
        found = []
        for element in self.snapshot.elements:
            if element.parent in ids:
                ids.add(element.id)
                found.append(element)
        return found

    def find_row(self, selector):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"{selector}: question row is missing")

    def test_question_row_right_padding(self):
        """Guards the right padding of question rows in the assessment questions tree.

        TreeQuestionRow.tsx commented out `paddingRight: '1.5rem'` on the row, so the Algebra
        topic badge and the points text moved 24 px right and the points clip at the viewport edge.
        """
        for selector, points, badge_left, points_right in QUESTION_ROWS:
            with self.subTest(row=selector):
                row = self.find_row(selector)
                padding = row.styles["padding-right"]
                self.assertEqual(padding, "24px", f"{selector}: padding-right expected 24px, got {padding}")
                inside = self.descendants(row)
                badges = [element for element in inside if element.own_text == "Algebra"]
                texts = [element for element in inside if element.own_text == points]
                self.assertTrue(badges and texts, f"{selector}: Algebra badge or points '{points}' is missing")
                badge, text = badges[0], texts[0]
                self.assertLessEqual(
                    abs(badge.box.x1 - badge_left),
                    1,
                    f"{badge.selector}: badge x expected {badge_left}, got {badge.box.x1}",
                )
                self.assertLessEqual(
                    abs(text.box.x2 - points_right),
                    1,
                    f"{text.selector}: points right edge expected {points_right}, got {text.box.x2}",
                )


if __name__ == "__main__":
    unittest.main()
