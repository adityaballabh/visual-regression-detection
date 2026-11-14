import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Background of the Savings Accounts card in the before snapshot, from #dcfce7
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_savings_card(self):
        for element in self.snapshot.elements:
            if not element.frames and element.tag == "h3" and element.own_text.strip() == "Savings Accounts":
                return self.snapshot.elements[element.parent]
        self.fail(f"{CARD_SELECTOR}: no card with heading 'Savings Accounts' found")

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which the change to the #cards section turned from #dcfce7 green to #fecaca pink although the design intent left the card unchanged."""
        card = self.find_savings_card()
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{card.selector}: background-color expected {EXPECTED_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
