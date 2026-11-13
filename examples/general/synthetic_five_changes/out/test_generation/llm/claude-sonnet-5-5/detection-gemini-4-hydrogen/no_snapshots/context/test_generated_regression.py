import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_green(self):
        """Guards the "Savings Accounts" card background in the cards section.

        The change to the cards row in after.html swapped the card's inline
        background from #dcfce7 (green) to #fecaca (pink), although the card
        was meant to stay untouched.
        """
        headings = [
            element
            for element in self.snapshot.elements
            if element.tag == "h3" and element.own_text.strip() == "Savings Accounts"
        ]
        self.assertEqual(len(headings), 1, "Expected one <h3> with the text 'Savings Accounts'")
        card = self.snapshot.elements[headings[0].parent]
        expected = "rgb(220, 252, 231)"
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            expected,
            f"{card.selector}: background-color expected {expected} but got {actual}",
        )
