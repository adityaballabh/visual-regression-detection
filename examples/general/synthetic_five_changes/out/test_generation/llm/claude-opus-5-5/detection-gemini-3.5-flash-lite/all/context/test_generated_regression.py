import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which turned red when the card's inline
        style in the #cards section changed from background:#dcfce7 to background:#fecaca."""
        matches = [e for e in self.snapshot.elements if e.frames == () and e.selector == SAVINGS_CARD]
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD}: Savings Accounts card not found")
        actual = matches[0].styles.get("background-color")
        expected = "rgb(220, 252, 231)"
        self.assertEqual(
            actual,
            expected,
            f"{SAVINGS_CARD} background-color: expected {expected}, got {actual}",
        )
