import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

HEADER = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > div:nth-child(1)"
    " > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1)"
)
ADD_COURSE_BUTTON = HEADER + " > button:nth-child(2)"

# Colors from the before snapshot, Bootstrap bg-primary header and btn-light button
EXPECTED_STYLES = [
    (HEADER, "background-color", "rgb(13, 110, 253)"),
    (ADD_COURSE_BUTTON, "background-color", "rgb(248, 249, 250)"),
    (ADD_COURSE_BUTTON, "border-top-color", "rgb(248, 249, 250)"),
    (ADD_COURSE_BUTTON, "color", "rgb(0, 0, 0)"),
]


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

    def test_courses_header_and_add_course_button_colors(self):
        """Guards the Courses card header and Add course button colors on the administrator courses page.

        The PR changed the header class from bg-primary to bg-secondary and the button from btn-light
        to btn-dark in the administrator courses card, though it was meant to only update text.
        """
        for selector, prop, expected in EXPECTED_STYLES:
            actual = self.find(selector).styles.get(prop)
            self.assertEqual(actual, expected, f"{selector}: {prop} expected {expected}, got {actual}")
