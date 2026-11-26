import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
OWN_TEXT = "Contact us at: info@educationalinstitute.com"
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact paragraph color against the heading recolor change.

        The change that darkened the section headings also set the inline style of the footer
        contact <p> to color:#1e40af, making its text dark blue on the bright blue footer
        instead of white.
        """
        matches = []
        for element in self.snapshot.elements:
            if element.selector == SELECTOR and not element.frames:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected one element, found {len(matches)}")
        element = matches[0]
        self.assertEqual(
            element.own_text, OWN_TEXT, f"{SELECTOR}: text expected {OWN_TEXT!r}, got {element.own_text!r}"
        )
        actual = element.styles.get("color")
        self.assertEqual(actual, EXPECTED_COLOR, f"{SELECTOR}: property color expected {EXPECTED_COLOR}, got {actual}")


if __name__ == "__main__":
    unittest.main()
