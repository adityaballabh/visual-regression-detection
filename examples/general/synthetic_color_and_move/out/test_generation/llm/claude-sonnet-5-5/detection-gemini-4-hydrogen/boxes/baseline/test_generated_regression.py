import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
EXPECTED_BACKGROUND = "rgb(37, 99, 235)"
EXPECTED_HEIGHT = 42
TOLERANCE = 1


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_button(self):
        for element in self.snapshot.elements:
            if element.selector == BUTTON_SELECTOR and not element.frames:
                return element
        self.fail(f"{BUTTON_SELECTOR}: element not found in snapshot")

    def test_open_account_button_keeps_primary_look(self):
        """Guards the 'Open an Account' primary button against turning danger red and oversized.

        The change that broke it replaced the button's inline style `padding:12px 24px;background:#2563eb`
        with `padding:24px 24px;background:#dc2626`.
        """
        button = self.find_button()

        background = button.styles["background-color"]
        self.assertEqual(
            background,
            EXPECTED_BACKGROUND,
            f"{BUTTON_SELECTOR}: background-color expected {EXPECTED_BACKGROUND}, got {background}",
        )

        self.assertAlmostEqual(
            button.box.height,
            EXPECTED_HEIGHT,
            delta=TOLERANCE,
            msg=f"{BUTTON_SELECTOR}: height expected {EXPECTED_HEIGHT}px, got {button.box.height}px",
        )


if __name__ == "__main__":
    unittest.main()
