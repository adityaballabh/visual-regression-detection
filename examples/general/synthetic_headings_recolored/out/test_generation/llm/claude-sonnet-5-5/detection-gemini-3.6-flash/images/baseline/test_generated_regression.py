import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FOOTER_CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line staying white on the blue footer.

        The heading recolor to #1e40af also changed the inline color of the footer
        contact paragraph from white to #1e40af, making it unreadable on the blue footer.
        """
        matches = [
            element
            for element in self.snapshot.elements
            if element.selector == FOOTER_CONTACT_SELECTOR and not element.frames
        ]
        self.assertEqual(len(matches), 1, f"{FOOTER_CONTACT_SELECTOR}: expected 1 element, found {len(matches)}")
        actual = matches[0].styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{FOOTER_CONTACT_SELECTOR}: property 'color' expected {EXPECTED_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
