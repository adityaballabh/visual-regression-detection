import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which turned red when its inline background changed from #dcfce7 to #fecaca."""
        savings_card = None
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == SAVINGS_CARD:
                savings_card = element
        self.assertIsNotNone(savings_card, f"{SAVINGS_CARD} is missing from the snapshot")
        actual = savings_card.styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{SAVINGS_CARD} background-color: expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
