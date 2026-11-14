import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Light green from the before snapshot, inline style background:#dcfce7
SAVINGS_CARD_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_stays_green(self):
        """Guards the 'Savings Accounts' card in #cards keeping its light green background.

        The redesign changed the card's inline style from background:#dcfce7 to
        background:#fecaca, turning it red although the card was meant to stay unchanged.
        """
        matches = []
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == SAVINGS_CARD_SELECTOR:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD_SELECTOR}: expected one element, found {len(matches)}")
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_CARD_BACKGROUND,
            f"{SAVINGS_CARD_SELECTOR} background-color: expected {SAVINGS_CARD_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
