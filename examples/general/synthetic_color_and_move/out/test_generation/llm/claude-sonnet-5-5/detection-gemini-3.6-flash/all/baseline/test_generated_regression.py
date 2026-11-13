import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

BUTTON_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
EXPECTED_BACKGROUND = "rgb(37, 99, 235)"
EXPECTED_HEIGHT = 42
EXPECTED_PADDING = "12px"
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
            if not element.frames and element.selector == BUTTON_SELECTOR:
                return element
        self.fail(f"{BUTTON_SELECTOR}: element not found in snapshot")

    def test_open_account_button_keeps_primary_color_and_size(self):
        """Guards the 'Open an Account' button against the change that turned it red and taller.

        The code change in after.html replaced its inline style `padding:12px 24px;background:#2563eb`
        with `padding:24px 24px;background:#dc2626`, so the primary blue button became red and 24px taller.
        """
        button = self.find_button()
        self.assertEqual(button.own_text, "Open an Account", f"{BUTTON_SELECTOR}: text")

        background = button.styles["background-color"]
        self.assertEqual(
            background,
            EXPECTED_BACKGROUND,
            f"{BUTTON_SELECTOR}: background-color expected {EXPECTED_BACKGROUND}, got {background}",
        )

        for side in ("padding-top", "padding-bottom"):
            padding = button.styles[side]
            self.assertEqual(
                padding,
                EXPECTED_PADDING,
                f"{BUTTON_SELECTOR}: {side} expected {EXPECTED_PADDING}, got {padding}",
            )

        self.assertAlmostEqual(
            button.box.height,
            EXPECTED_HEIGHT,
            delta=TOLERANCE,
            msg=f"{BUTTON_SELECTOR}: height expected {EXPECTED_HEIGHT}px, got {button.box.height}px",
        )
