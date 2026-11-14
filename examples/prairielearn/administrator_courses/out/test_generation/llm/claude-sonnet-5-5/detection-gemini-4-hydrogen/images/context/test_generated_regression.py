import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

HEADER_SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > "
    "div:nth-child(1) > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > "
    "div:nth-child(1)"
)
BUTTON_SELECTOR = HEADER_SELECTOR + " > button:nth-child(2)"

EXPECTED_STYLES = {
    HEADER_SELECTOR: {
        "background-color": "rgb(13, 110, 253)",
    },
    BUTTON_SELECTOR: {
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
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"Element {selector} not found in snapshot")

    def test_courses_card_header_and_add_button_colors(self):
        """Guards the Courses card header and its 'Add course' button keeping the primary
        blue header and light button colors. Broken by the administratorCourses.html.tsx
        change that swapped bg-primary for bg-secondary and btn-light for btn-dark while
        only the text was meant to change.
        """
        for selector, expected in EXPECTED_STYLES.items():
            element = self.find(selector)
            for prop, value in expected.items():
                actual = element.styles.get(prop)
                self.assertEqual(
                    actual,
                    value,
                    f"{selector}: {prop} expected {value!r} but got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
