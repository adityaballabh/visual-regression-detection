import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
# Footer text color from the before snapshot, white on the blue footer
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line, whose inline color went from white to #1e40af in the
        change meant to recolor only the section headings dark blue."""
        matches = []
        for element in self.snapshot.elements:
            if not element.frames and element.selector == CONTACT_SELECTOR:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{CONTACT_SELECTOR}: element not found")
        contact = matches[0]
        self.assertEqual(
            contact.own_text,
            CONTACT_TEXT,
            f"{CONTACT_SELECTOR}: text expected {CONTACT_TEXT!r}, got {contact.own_text!r}",
        )
        actual = contact.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{CONTACT_SELECTOR}: color expected {EXPECTED_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
