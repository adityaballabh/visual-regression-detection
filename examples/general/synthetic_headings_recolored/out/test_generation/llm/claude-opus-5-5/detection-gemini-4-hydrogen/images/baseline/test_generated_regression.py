import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
# White text taken from the before snapshot, readable on the blue footer
CONTACT_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line against turning dark blue on the blue footer.

        The heading recolor in after.html also changed the inline style of the footer
        contact <p> from color:white to color:#1e40af, which made it nearly unreadable.
        """
        contact = None
        for element in self.snapshot.elements:
            if not element.frames and element.selector == CONTACT_SELECTOR:
                contact = element
        self.assertIsNotNone(contact, f"{CONTACT_SELECTOR} is missing from the snapshot")
        actual = contact.styles.get("color")
        self.assertEqual(
            actual,
            CONTACT_COLOR,
            f"{CONTACT_SELECTOR} color: expected {CONTACT_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
