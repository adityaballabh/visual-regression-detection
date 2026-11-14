import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Bootstrap primary blue on the Courses card header in the before snapshot
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_courses_header(self):
        card = None
        for element in self.snapshot.elements:
            if element.attributes.get("id") == "courses":
                card = element
        self.assertIsNotNone(card, "No element with id 'courses' in the snapshot")
        for element in self.snapshot.elements:
            classes = element.attributes.get("class", "").split()
            if element.parent == card.id and "card-header" in classes:
                return element
        self.fail("No .card-header inside #courses in the snapshot")

    def test_courses_card_header_is_primary_blue(self):
        """Guards the Courses card header on the administrator courses page, which turned dark grey
        when CoursesCard in administratorCourses.html.tsx swapped bg-primary for bg-secondary."""
        header = self.find_courses_header()
        background = header.styles.get("background-color")
        self.assertEqual(
            background,
            EXPECTED_BACKGROUND,
            f"{header.selector}: background-color expected {EXPECTED_BACKGROUND}, got {background}",
        )


if __name__ == "__main__":
    unittest.main()
