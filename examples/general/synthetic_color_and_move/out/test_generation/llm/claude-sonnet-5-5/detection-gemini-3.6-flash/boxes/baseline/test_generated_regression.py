import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
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

    def test_open_account_button_is_blue_and_compact(self):
        """Guards the 'Open an Account' primary button against turning destructive red and tall.

        The change restyled the button from background #2563eb with padding 12px 24px to
        background #dc2626 with padding 24px 24px, which also grew its height by 24px.
        """
        matches = [e for e in self.snapshot.elements if e.selector == SELECTOR and not e.frames]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected one element, found {len(matches)}")
        button = matches[0]
        self.assertEqual(button.own_text, "Open an Account", f"{SELECTOR}: text")
        for prop, expected in EXPECTED_STYLES.items():
            actual = button.styles.get(prop)
            self.assertEqual(actual, expected, f"{SELECTOR}: {prop} expected {expected}, actual {actual}")
        self.assertAlmostEqual(
            button.box.height,
            EXPECTED_HEIGHT,
            delta=1,
            msg=f"{SELECTOR}: height expected {EXPECTED_HEIGHT}, actual {button.box.height}",
        )


if __name__ == "__main__":
    unittest.main()
