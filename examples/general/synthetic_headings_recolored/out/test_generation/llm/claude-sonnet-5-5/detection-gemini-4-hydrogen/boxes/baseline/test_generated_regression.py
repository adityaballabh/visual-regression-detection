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
        """Guards the footer contact paragraph keeping its white text on the blue footer.

        The change that recolored the h2 headings to #1e40af also changed the footer
        paragraph's inline style from color:white to color:#1e40af.
        """
        matches = [e for e in self.snapshot.elements if e.selector == FOOTER_CONTACT_SELECTOR and not e.frames]
        self.assertEqual(len(matches), 1, f"{FOOTER_CONTACT_SELECTOR}: element not found")
        actual = matches[0].styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{FOOTER_CONTACT_SELECTOR}: property 'color' expected {EXPECTED_COLOR} but was {actual}",
        )


if __name__ == "__main__":
    unittest.main()
