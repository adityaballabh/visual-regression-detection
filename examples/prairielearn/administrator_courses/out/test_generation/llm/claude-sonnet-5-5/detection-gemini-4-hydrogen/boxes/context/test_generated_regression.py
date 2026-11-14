import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) "
    "> div:nth-child(1) > main:nth-child(2) > div:nth-child(3) > div:nth-child(2) "
    "> div:nth-child(1)"
)
HEADER_SELECTOR = PREFIX
BUTTON_SELECTOR = PREFIX + " > button:nth-child(2)"

# Expected values taken from the before snapshot
EXPECTED_STYLES = {
    HEADER_SELECTOR: {
        "background-color": "rgb(13, 110, 253)",
    },
    BUTTON_SELECTOR: {
        "background-color": "rgb(248, 249, 250)",
        "color": "rgb(0, 0, 0)",
        "border-top-color": "rgb(248, 249, 250)",
        "border-right-color": "rgb(248, 249, 250)",
        "border-bottom-color": "rgb(248, 249, 250)",
        "border-left-color": "rgb(248, 249, 250)",
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
        self.fail(f"Element not found: {selector}")

    def test_courses_card_header_and_add_button_keep_color_scheme(self):
        """Guards the administrator courses card header and 'Add course' button colors.

        The change to administratorCourses.html.tsx switched the header from bg-primary
        to bg-secondary and the button from btn-light to btn-dark while only the card
        text was meant to be updated.
        """
        for selector, expected in EXPECTED_STYLES.items():
            element = self.find(selector)
            for prop, want in expected.items():
                got = element.styles.get(prop)
                self.assertEqual(
                    got,
                    want,
                    f"{selector}: {prop} expected {want!r} but got {got!r}",
                )


if __name__ == "__main__":
    unittest.main()
