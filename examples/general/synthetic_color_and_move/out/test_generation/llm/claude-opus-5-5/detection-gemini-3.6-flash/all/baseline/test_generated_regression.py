import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_element(self, selector):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"{selector}: element missing from snapshot")

    def test_open_account_button_keeps_blue_and_size(self):
        """Guards the 'Open an Account' hero button against turning red and oversized.

        Caused by the inline style change in the hero section, background #2563eb -> #dc2626
        and padding 12px 24px -> 24px 24px.
        """
        button = self.find_element(BUTTON_SELECTOR)
        expected_styles = {
            "background-color": "rgb(37, 99, 235)",
            "padding-top": "12px",
            "padding-bottom": "12px",
        }
        for name, expected in expected_styles.items():
            actual = button.styles.get(name)
            self.assertEqual(actual, expected, f"{BUTTON_SELECTOR}: {name} expected {expected}, got {actual}")
        self.assertAlmostEqual(
            button.box.height,
            42,
            delta=1,
            msg=f"{BUTTON_SELECTOR}: height expected 42px, got {button.box.height}px",
        )


if __name__ == "__main__":
    unittest.main()
