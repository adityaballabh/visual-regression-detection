import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
SAVINGS_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_light_green(self):
        """Guards the 'Savings Accounts' card keeping its light green background.

        The change from before.html to after.html set the card's inline background from
        #dcfce7 to #fecaca, turning it red like an error state although the card was not
        meant to change.
        """
        cards = [e for e in self.snapshot.elements if e.selector == SAVINGS_CARD and not e.frames]
        self.assertEqual(len(cards), 1, f"{SAVINGS_CARD}: expected one element, found {len(cards)}")
        actual = cards[0].styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_BACKGROUND,
            f"{SAVINGS_CARD}: background-color expected {SAVINGS_BACKGROUND}, actual {actual}",
        )


if __name__ == "__main__":
    unittest.main()
