import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_light_green(self):
        """Guards the "Savings Accounts" card background, which must stay light green.

        Broken by the change of the card's inline style from background:#dcfce7 to
        background:#fecaca in the #cards section, turning the card light pink.
        """
        matches = [
            element
            for element in self.snapshot.elements
            if not element.frames and element.selector == SAVINGS_CARD_SELECTOR
        ]
        self.assertEqual(
            len(matches), 1, f"{SAVINGS_CARD_SELECTOR}: expected exactly one element, found {len(matches)}"
        )
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SAVINGS_CARD_SELECTOR}: property background-color expected {EXPECTED_BACKGROUND}, actual {actual}",
        )


if __name__ == "__main__":
    unittest.main()
