import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Computed background of the Courses card header in the before snapshot (Bootstrap bg-primary)
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_courses_header(self):
        for element in self.snapshot.elements:
            if "card-header" not in element.attributes.get("class", "").split():
                continue
            if element.parent is None:
                continue
            if self.snapshot.elements[element.parent].attributes.get("id") == "courses":
                return element
        self.fail("No .card-header found inside #courses")

    def test_courses_card_header_is_primary_blue(self):
        """Guards the Courses card header on the administrator courses page staying primary blue.

        Regressed when administratorCourses.html.tsx changed the header class from
        bg-primary to bg-secondary (and the Add course button from btn-light to btn-dark).
        """
        header = self.find_courses_header()
        actual = header.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{header.selector}: background-color expected {EXPECTED_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
