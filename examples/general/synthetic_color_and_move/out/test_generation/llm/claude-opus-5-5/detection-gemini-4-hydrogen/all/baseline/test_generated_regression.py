import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
# Values from the before snapshot
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

    def test_open_account_button_keeps_primary_style(self):
        """Guards the hero 'Open an Account' button turning red and 24px taller.

        Caused by the inline style on the hero button in before.html changing from
        padding:12px 24px;background:#2563eb to padding:24px 24px;background:#dc2626.
        """
        button = self.find_button()
        for name, expected in EXPECTED_STYLES.items():
            actual = button.styles.get(name)
            self.assertEqual(actual, expected, f"{BUTTON_SELECTOR}: {name} expected {expected}, got {actual}")
        self.assertLessEqual(
            abs(button.box.height - EXPECTED_HEIGHT),
            1,
            f"{BUTTON_SELECTOR}: height expected {EXPECTED_HEIGHT}px, got {button.box.height}px",
        )


if __name__ == "__main__":
    unittest.main()
