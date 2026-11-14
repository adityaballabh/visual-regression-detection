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
        """Guards the Savings Accounts card color, which turned pink when its inline background changed from #dcfce7 to #fecaca in the #cards section."""
        matches = [
            element for element in self.snapshot.elements if element.frames == () and element.selector == SAVINGS_CARD
        ]
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD} not found in the snapshot")
        card = matches[0]
        expected = "rgb(220, 252, 231)"
        actual = card.styles.get("background-color")
        self.assertEqual(actual, expected, f"{SAVINGS_CARD} background-color: expected {expected}, got {actual}")


if __name__ == "__main__":
    unittest.main()
