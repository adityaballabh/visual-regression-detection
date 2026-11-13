import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CARD_HEADER_SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > "
    "div:nth-child(1) > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > div:nth-child(1)"
)
ADD_COURSE_SELECTOR = CARD_HEADER_SELECTOR + " > button:nth-child(2)"

EXPECTED_STYLES = {
    CARD_HEADER_SELECTOR: {
        "background-color": "rgb(13, 110, 253)",
    },
    ADD_COURSE_SELECTOR: {
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
        self.fail(f"{selector}: element not found in snapshot")

    def test_courses_card_header_and_add_button_colors(self):
        """Guards the administrator courses card colors against the change in
        administratorCourses.html.tsx that swapped the header's bg-primary for bg-secondary
        and the "Add course" button's btn-light for btn-dark."""
        for selector, expected_styles in EXPECTED_STYLES.items():
            element = self.find(selector)
            for prop, expected in expected_styles.items():
                actual = element.styles.get(prop)
                self.assertEqual(
                    actual,
                    expected,
                    f"{selector}: {prop} expected {expected!r} but got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
