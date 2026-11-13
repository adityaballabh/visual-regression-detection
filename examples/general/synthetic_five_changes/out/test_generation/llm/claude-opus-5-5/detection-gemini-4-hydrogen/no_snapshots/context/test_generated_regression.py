import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Soft pastel green, #dcfce7 in before.html
SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"{selector} is missing from the snapshot")

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which the change to the #cards section
        switched from #dcfce7 green to #fecaca pink although the card was meant to stay unchanged"""
        card = self.find(SAVINGS_CARD)
        heading = card.selector + " > h3:nth-child(1)"
        self.assertEqual(self.find(heading).own_text, "Savings Accounts", f"{heading} text")
        actual = card.styles["background-color"]
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{SAVINGS_CARD} background-color: expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
