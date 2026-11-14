import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
# Computed styles of the hero button in the before snapshot
EXPECTED_STYLES = {
    "background-color": "rgb(37, 99, 235)",
    "padding-top": "12px",
    "padding-bottom": "12px",
}
EXPECTED_HEIGHT = 42


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_button(self):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == BUTTON_SELECTOR:
                return element
        self.fail(f"{BUTTON_SELECTOR}: element not found")

    def test_open_account_button_stays_blue_and_compact(self):
        """Guards the 'Open an Account' hero button, which before.html -> after.html turned red
        (background #2563eb -> #dc2626) and made 24px taller (padding 12px 24px -> 24px 24px)."""
        button = self.find_button()
        self.assertEqual(button.own_text, "Open an Account", f"{BUTTON_SELECTOR}: text")
        for name, expected in EXPECTED_STYLES.items():
            actual = button.styles.get(name)
            self.assertEqual(actual, expected, f"{BUTTON_SELECTOR}: {name} expected {expected}, got {actual}")
        self.assertAlmostEqual(
            button.box.height,
            EXPECTED_HEIGHT,
            delta=1,
            msg=f"{BUTTON_SELECTOR}: height expected {EXPECTED_HEIGHT}px, got {button.box.height}px",
        )


if __name__ == "__main__":
    unittest.main()
