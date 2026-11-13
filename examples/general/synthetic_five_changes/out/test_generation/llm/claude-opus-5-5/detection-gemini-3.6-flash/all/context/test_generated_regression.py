import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Green card background from the before snapshot, from the inline style background:#dcfce7
SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_unchanged(self):
        """Guards the Savings Accounts card background, which the change turned from #dcfce7 green to #fecaca red in its inline style."""
        matches = []
        for element in self.snapshot.elements:
            if element.selector == SAVINGS_CARD_SELECTOR and not element.frames:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD_SELECTOR}: Savings Accounts card not found")
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{SAVINGS_CARD_SELECTOR}: background-color expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
