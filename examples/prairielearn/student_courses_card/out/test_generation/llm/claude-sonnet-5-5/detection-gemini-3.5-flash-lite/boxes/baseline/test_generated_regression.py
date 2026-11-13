import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > "
    "div:nth-child(1) > main:nth-child(1) > div:nth-child(1) > div:nth-child(5) > "
    "div:nth-child(1) > div:nth-child(1)"
)
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_courses_card_header_is_primary_blue(self):
        """Guards the student courses card header background.

        StudentCoursesCard.tsx changed the header class from bg-primary to
        bg-secondary, turning the header from blue to gray.
        """
        matches = [element for element in self.snapshot.elements if element.selector == SELECTOR and not element.frames]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected one element, found {len(matches)}")
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SELECTOR}: background-color expected {EXPECTED_BACKGROUND!r}, got {actual!r}",
        )


if __name__ == "__main__":
    unittest.main()
