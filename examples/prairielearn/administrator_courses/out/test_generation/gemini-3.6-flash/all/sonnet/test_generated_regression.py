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


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def _find(self, selector):
        for el in self.snapshot.elements:
            if el.selector == selector and not el.frames:
                return el
        self.fail(f"Element not found: {selector}")

    def _check(self, selector, prop, expected):
        el = self._find(selector)
        actual = el.styles.get(prop)
        self.assertEqual(
            actual,
            expected,
            f"{selector}: {prop} expected {expected!r} but got {actual!r}",
        )

    def test_card_header_and_add_course_button_colors(self):
        """Guards the 'Courses' card header and 'Add course' button colors.

        The administrator courses card change swapped the header classes from
        bg-primary to bg-secondary and the button from btn-light to btn-dark,
        turning the blue header grey and the light button dark.
        """
        self._check(HEADER_SELECTOR, "background-color", "rgb(13, 110, 253)")
        self._check(BUTTON_SELECTOR, "background-color", "rgb(248, 249, 250)")
        self._check(BUTTON_SELECTOR, "color", "rgb(0, 0, 0)")
        self._check(BUTTON_SELECTOR, "border-top-color", "rgb(248, 249, 250)")


if __name__ == "__main__":
    unittest.main()
