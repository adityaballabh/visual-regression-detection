import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_element(self, attribute, value):
        for element in self.snapshot.elements:
            if element.frames == () and element.attributes.get(attribute) == value:
                return element
        self.fail(f"No element with {attribute}={value!r}")

    def find_child(self, parent, selector_suffix):
        selector = f"{parent.selector} > {selector_suffix}"
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"No element at {selector}")

    def assert_style(self, element, name, expected):
        actual = element.styles.get(name)
        self.assertEqual(
            actual,
            expected,
            f"{element.selector}: {name} expected {expected}, got {actual}",
        )

    def test_courses_card_header_keeps_primary_colors(self):
        """Guards the administrator Courses card header colors.

        The PR that only meant to update the card text also changed the header from
        `bg-primary` to `bg-secondary` and the Add course button from `btn-light` to
        `btn-dark` in administratorCourses.html.tsx, turning the blue header gray and
        the light button dark.
        """
        courses_card = self.find_element("id", "courses")
        # The header is the first child of the card
        header = self.find_child(courses_card, "div:nth-child(1)")
        add_course_button = self.find_element("aria-label", "Add course")

        self.assert_style(header, "background-color", "rgb(13, 110, 253)")
        self.assert_style(add_course_button, "background-color", "rgb(248, 249, 250)")
        self.assert_style(add_course_button, "color", "rgb(0, 0, 0)")
