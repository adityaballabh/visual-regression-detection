import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
# White text from the before snapshot, readable on the blue footer
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact email color, which turned dark blue on the blue footer
        when the heading recolor also changed the contact <p> inline style from white to #1e40af."""
        matches = []
        for element in self.snapshot.elements:
            if element.selector == CONTACT_SELECTOR and not element.frames:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{CONTACT_SELECTOR}: element missing from snapshot")
        actual = matches[0].styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{CONTACT_SELECTOR}: color expected {EXPECTED_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
