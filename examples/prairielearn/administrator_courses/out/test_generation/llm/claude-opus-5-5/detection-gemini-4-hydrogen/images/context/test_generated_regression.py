import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

HEADER = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
    " > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1)"
)
ADD_BUTTON = HEADER + " > button:nth-child(2)"

# Colors from the before snapshot, primary blue header with a light button
EXPECTED_STYLES = {
    HEADER: {"background-color": "rgb(13, 110, 253)"},
    ADD_BUTTON: {
        "background-color": "rgb(248, 249, 250)",
        "border-top-color": "rgb(248, 249, 250)",
        "border-right-color": "rgb(248, 249, 250)",
        "border-bottom-color": "rgb(248, 249, 250)",
        "border-left-color": "rgb(248, 249, 250)",
        "color": "rgb(0, 0, 0)",
    },
}


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element not found")

    def test_courses_card_header_colors(self):
        """Guards the Courses card header and its 'Add course' button colors.

        CoursesCard in administratorCourses.html.tsx swapped bg-primary for bg-secondary on the
        header and btn-light for btn-dark on the button, though the change was meant to update text only.
        """
        for selector, styles in EXPECTED_STYLES.items():
            element = self.find(selector)
            for name, expected in styles.items():
                actual = element.styles.get(name)
                self.assertEqual(actual, expected, f"{selector}: {name} expected {expected}, got {actual}")


if __name__ == "__main__":
    unittest.main()
