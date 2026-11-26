import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
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

        Regression: the change that recolored the section headings to #1e40af also
        set the footer `<p>` "Contact us at: ..." to color:#1e40af instead of white.
        """
        contacts = []
        for element in self.snapshot.elements:
            if element.tag.lower() == "p" and CONTACT_TEXT in element.own_text:
                contacts.append(element)
        self.assertEqual(len(contacts), 1, f"Expected one <p> with text {CONTACT_TEXT!r}, found {len(contacts)}")
        contact = contacts[0]
        actual = contact.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{contact.selector}: property 'color' expected {EXPECTED_COLOR} but was {actual}",
        )
