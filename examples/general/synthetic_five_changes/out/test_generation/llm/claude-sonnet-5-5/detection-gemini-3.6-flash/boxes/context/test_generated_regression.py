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

    def test_savings_card_background(self):
        """Guards the 'Savings Accounts' card background, which must stay light green.

        The regression changed its inline background from #dcfce7 to #fecaca in after.html.
        """
        cards = [e for e in self.snapshot.elements if e.selector == SELECTOR and not e.frames]
        self.assertEqual(len(cards), 1, f"{SELECTOR}: expected one element, found {len(cards)}")
        actual = cards[0].styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{SELECTOR}: background-color expected {EXPECTED_BACKGROUND}, actual {actual}",
        )


if __name__ == "__main__":
    unittest.main()
