import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SAVINGS_CARD = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"
# Light green from the before snapshot, set by background:#dcfce7
SAVINGS_BACKGROUND = "rgb(220, 252, 231)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_savings_card_keeps_green_background(self):
        """Guards the Savings Accounts card background, which the change in the #cards section
        switched from background:#dcfce7 (light green) to background:#fecaca (light red)."""
        matches = []
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == SAVINGS_CARD:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SAVINGS_CARD}: Savings Accounts card not found")
        actual = matches[0].styles.get("background-color")
        self.assertEqual(
            actual,
            SAVINGS_BACKGROUND,
            f"{SAVINGS_CARD} background-color: expected {SAVINGS_BACKGROUND}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
