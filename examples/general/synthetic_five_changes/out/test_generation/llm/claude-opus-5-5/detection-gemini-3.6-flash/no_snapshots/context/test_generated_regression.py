import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_savings_card(self):
        for element in self.snapshot.elements:
            if element.tag == "h3" and element.own_text.strip() == "Savings Accounts":
                return self.snapshot.elements[element.parent]
        self.fail("No h3 with text 'Savings Accounts' found in the snapshot")

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which the change in #cards turned from #dcfce7 green to #fecaca pink."""
        card = self.find_savings_card()
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{card.frames} {card.selector}: background-color expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
