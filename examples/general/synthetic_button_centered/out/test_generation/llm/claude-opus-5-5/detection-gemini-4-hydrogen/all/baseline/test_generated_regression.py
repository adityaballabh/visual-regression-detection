import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABEL_SELECTORS = [
    f"{FORM} > div:nth-child(1) > label:nth-child(1)",
    f"{FORM} > div:nth-child(2) > label:nth-child(1)",
]
# Taken from the before snapshot, labels inherit the default alignment
EXPECTED_TEXT_ALIGN = "start"


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
        self.fail(f"{selector}: element missing from snapshot")

    def test_signup_labels_stay_left_aligned(self):
        """Guards the Username and Password labels in the Sign Up form against becoming centered.

        The change that centered the Sign Up button (intended) also added text-align:center
        to the inline style of both form labels in the #trial section.
        """
        for selector in LABEL_SELECTORS:
            with self.subTest(selector=selector):
                label = self.find_element(selector)
                actual = label.styles.get("text-align")
                self.assertEqual(
                    actual,
                    EXPECTED_TEXT_ALIGN,
                    f"{selector}: text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
