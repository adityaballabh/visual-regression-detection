import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
EXPECTED_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_background_is_light_green(self):
        """Guards the Savings Accounts card background staying light green.

        Regressed when the second card's inline style changed from background:#dcfce7
        to background:#fecaca in the #cards section while other page edits were made.
        """
        cards = [e for e in self.snapshot.elements if e.selector == SAVINGS_CARD and not e.frames]
        self.assertEqual(len(cards), 1, f"{SAVINGS_CARD}: expected one element, found {len(cards)}")
        card = cards[0]
        self.assertEqual(card.tag, "div", f"{SAVINGS_CARD}: tag expected 'div', got {card.tag!r}")
        actual = card.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SAVINGS_CARD}: background-color expected {EXPECTED_BACKGROUND!r}, got {actual!r}",
        )
