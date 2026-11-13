import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Light green from the before snapshot, the card was meant to stay unchanged
SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_element(self, selector, frames):
        for element in self.snapshot.elements:
            if element.selector == selector and list(element.frames) == frames:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_savings_card_background_unchanged(self):
        """Guards the Savings Accounts card background, which the change in the #cards section
        switched from #dcfce7 (light green) to #fecaca (light red) despite the card being meant to stay unchanged."""
        card = self.find_element(SAVINGS_CARD_SELECTOR, [])
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{SAVINGS_CARD_SELECTOR}: background-color expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
