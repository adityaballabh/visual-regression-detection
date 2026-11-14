import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

COURSES_HEADER = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
    " > main:nth-child(1) > div:nth-child(1) > div:nth-child(5) > div:nth-child(1) > div:nth-child(1)"
)
# Primary blue from the before snapshot, matching the Development Mode header
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"{selector}: element missing from snapshot")

    def test_courses_header_background_is_primary(self):
        """Guards the Courses card header turning from blue to gray, caused by StudentCoursesCard.tsx
        swapping the header class bg-primary for bg-secondary."""
        header = self.find(COURSES_HEADER)
        actual = header.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{COURSES_HEADER}: background-color expected {EXPECTED_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
