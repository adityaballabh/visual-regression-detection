import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Soft green from the before snapshot
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_unchanged(self):
        """Guards the Savings Accounts card color, which broke when the card background
        changed from #dcfce7 to #fecaca (pink) in the second cards-section div of after.html."""
        card = None
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == SAVINGS_CARD:
                card = element
        self.assertIsNotNone(card, f"{SAVINGS_CARD}: element is missing from the snapshot")
        actual = card.styles["background-color"]
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SAVINGS_CARD}: background-color expected {EXPECTED_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
