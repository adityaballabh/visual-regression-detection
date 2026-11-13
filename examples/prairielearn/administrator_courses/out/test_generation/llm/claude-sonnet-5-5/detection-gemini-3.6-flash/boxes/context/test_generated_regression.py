import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CARD_HEADER_SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > "
    "div:nth-child(1) > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) > "
    "div:nth-child(1)"
)
ADD_COURSE_SELECTOR = CARD_HEADER_SELECTOR + " > button:nth-child(2)"

# Expected values come from the before snapshot
EXPECTED_STYLES = {
    CARD_HEADER_SELECTOR: {
        "background-color": "rgb(13, 110, 253)",
    },
    ADD_COURSE_SELECTOR: {
        "background-color": "rgb(248, 249, 250)",
        "border-top-color": "rgb(248, 249, 250)",
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
        self.fail(f"Element {selector} not found in the snapshot")

    def test_courses_card_header_and_add_button_keep_their_colors(self):
        """Guards the Courses card header and 'Add course' button colors.

        The change to the administrator courses card swapped bg-primary for bg-secondary on
        the card header and btn-light for btn-dark on the button, although only the card
        text was meant to change.
        """
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
