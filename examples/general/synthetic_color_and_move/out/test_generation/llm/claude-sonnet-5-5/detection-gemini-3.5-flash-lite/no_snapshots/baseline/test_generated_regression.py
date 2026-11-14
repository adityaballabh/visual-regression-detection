import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_TEXT = "Open an Account"
# Primary blue (#2563eb) from the BEFORE snapshot
EXPECTED_BACKGROUND = "rgb(37, 99, 235)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_button(self):
        for element in self.snapshot.elements:
            if element.frames == () and element.tag.lower() == "button" and element.own_text.strip() == BUTTON_TEXT:
                return element
        self.fail(f"No <button> with text {BUTTON_TEXT!r} found in the snapshot")

    def test_open_account_button_keeps_primary_blue(self):
        """Guards the 'Open an Account' hero button color (blue, not red).

        Broken by the change in before.html -> after.html that switched the button's
        inline background from #2563eb to #dc2626 (and raised its vertical padding).
        """
        button = self.find_button()
        actual = button.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{button.selector}: background-color expected {EXPECTED_BACKGROUND!r}, got {actual!r}",
        )


if __name__ == "__main__":
    unittest.main()
