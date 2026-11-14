import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CARD_HEADER = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1) > "
    "main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1)"
)
ADD_COURSE_BUTTON = CARD_HEADER + " > button:nth-child(2)"

# Expected values from the before snapshot
EXPECTED_STYLES = {
    CARD_HEADER: {"background-color": "rgb(13, 110, 253)"},
    ADD_COURSE_BUTTON: {
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

    def find_element(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element not found")

    def test_courses_card_header_keeps_primary_colors(self):
        """Guards the Courses card header on the administrator courses page, whose blue bg-primary
        header and btn-light "Add course" button turned gray and dark when administratorCourses.html.tsx
        swapped them for bg-secondary and btn-dark"""
        for selector, styles in EXPECTED_STYLES.items():
            element = self.find_element(selector)
            for name, expected in styles.items():
                actual = element.styles.get(name)
                with self.subTest(selector=selector, property=name):
                    self.assertEqual(actual, expected, f"{selector}: {name} expected {expected}, got {actual}")


if __name__ == "__main__":
    unittest.main()
