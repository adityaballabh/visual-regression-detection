import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
# White text on the blue footer, from the before snapshot
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line, whose color changed from white to #1e40af on the #3b82f6 footer and became unreadable."""
        contact = None
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == CONTACT_SELECTOR:
                contact = element
        self.assertIsNotNone(contact, f"{CONTACT_SELECTOR} is missing")
        self.assertEqual(
            contact.own_text,
            CONTACT_TEXT,
            f"{CONTACT_SELECTOR} text: expected {CONTACT_TEXT!r}, got {contact.own_text!r}",
        )
        color = contact.styles["color"]
        self.assertEqual(color, EXPECTED_COLOR, f"{CONTACT_SELECTOR} color: expected {EXPECTED_COLOR}, got {color}")


if __name__ == "__main__":
    unittest.main()
