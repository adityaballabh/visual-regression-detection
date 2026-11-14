import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Primary blue of the Courses card header in the before snapshot
EXPECTED_HEADER_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def courses_header(self):
        by_id = {element.id: element for element in self.snapshot.elements}
        for element in self.snapshot.elements:
            if element.tag == "h2" and element.own_text == "Courses":
                return by_id[element.parent]
        self.fail("No h2 with text 'Courses' found in the snapshot")

    def test_courses_card_header_background(self):
        """Guards the Courses card header turning grey, caused by StudentCoursesCard.tsx swapping bg-primary for bg-secondary."""
        header = self.courses_header()
        actual = header.styles["background-color"]
        self.assertEqual(
            actual,
            EXPECTED_HEADER_BACKGROUND,
            f"{header.selector}: background-color expected {EXPECTED_HEADER_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
