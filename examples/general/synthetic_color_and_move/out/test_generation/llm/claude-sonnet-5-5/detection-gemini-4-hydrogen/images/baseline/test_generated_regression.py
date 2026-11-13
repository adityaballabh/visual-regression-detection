import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_open_account_button_style(self):
        """Guards the 'Open an Account' button against the regression where its background
        turned from blue to red and its vertical padding doubled from 12px to 24px, caused by
        the inline style change from "padding:12px 24px;background:#2563eb" to
        "padding:24px 24px;background:#dc2626" in after.html."""
        matches = [e for e in self.snapshot.elements if e.selector == SELECTOR and not e.frames]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected exactly one element, found {len(matches)}")
        button = matches[0]

        self.assertEqual(button.own_text, "Open an Account", f"{SELECTOR}: own_text")
        expected_styles = {
            "background-color": "rgb(37, 99, 235)",
            "padding-top": "12px",
            "padding-bottom": "12px",
        }
        for prop, expected in expected_styles.items():
            actual = button.styles.get(prop)
            self.assertEqual(actual, expected, f"{SELECTOR}: {prop} expected {expected!r}, got {actual!r}")

        self.assertAlmostEqual(
            button.box.height,
            42,
            delta=1,
            msg=f"{SELECTOR}: height expected 42, got {button.box.height}",
        )
