import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CARD_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_green(self):
        """Guards the 'Savings Accounts' card background staying light green (rgb(220, 252, 231)).

        Regression caused by the after.html change of that card's inline style from
        `background:#dcfce7` to `background:#fecaca`, which turned the card red.
        """
        cards = [
            element for element in self.snapshot.elements if not element.frames and element.selector == CARD_SELECTOR
        ]
        self.assertEqual(len(cards), 1, f"{CARD_SELECTOR}: expected exactly one element, found {len(cards)}")
        card = cards[0]
        self.assertIn("Savings Accounts", self._text_of(card), f"{CARD_SELECTOR}: not the Savings Accounts card")
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{CARD_SELECTOR} property background-color: expected {EXPECTED_BACKGROUND}, got {actual}",
        )

    def _text_of(self, card):
        texts = []
        for element in self.snapshot.elements:
            if element.parent == card.id:
                texts.append(element.own_text)
        return " ".join(texts)


if __name__ == "__main__":
    unittest.main()
