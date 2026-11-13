import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
SAVINGS_GREEN = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_stays_green(self):
        """Guards the Savings Accounts card background, which the #cards section change turned from #dcfce7 green to #fecaca red."""
        matches = []
        for element in self.snapshot.elements:
            if not element.frames and element.selector == SAVINGS_CARD:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD}: Savings Accounts card not found")
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_GREEN,
            f"{SAVINGS_CARD}: background-color expected {SAVINGS_GREEN}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
