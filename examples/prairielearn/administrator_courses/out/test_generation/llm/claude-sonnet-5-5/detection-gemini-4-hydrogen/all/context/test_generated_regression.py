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
    HEADER_SELECTOR: {"background-color": "rgb(13, 110, 253)"},
    BUTTON_SELECTOR: {
        "background-color": "rgb(248, 249, 250)",
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

    def test_courses_card_header_and_add_button_keep_their_colors(self):
        """Guards the Courses card header and Add course button colors.

        The change to administratorCourses.html.tsx swapped bg-primary for bg-secondary
        on the card header and btn-light for btn-dark on the Add course button, although
        the intent was only to update text.
        """
        for selector, styles in EXPECTED_STYLES.items():
            element = self.find(selector)
            for prop, expected in styles.items():
                actual = element.styles.get(prop)
                self.assertEqual(
                    actual,
                    expected,
                    f"{selector}: {prop} expected {expected!r} but got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
