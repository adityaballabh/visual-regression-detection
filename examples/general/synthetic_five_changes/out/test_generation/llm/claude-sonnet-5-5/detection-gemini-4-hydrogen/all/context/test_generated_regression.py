import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_accounts_card_background(self):
        """Guards the Savings Accounts card background staying light green (rgb(220, 252, 231)).

        The regression came from the code change that replaced the card's inline
        style background #dcfce7 with #fecaca in after.html.
        """
        card = None
        for element in self.snapshot.elements:
            if not element.frames and element.selector == SELECTOR:
                card = element
                break
        self.assertIsNotNone(card, f"{SELECTOR}: element not found in snapshot")
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SELECTOR}: background-color expected {EXPECTED_BACKGROUND} but got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
