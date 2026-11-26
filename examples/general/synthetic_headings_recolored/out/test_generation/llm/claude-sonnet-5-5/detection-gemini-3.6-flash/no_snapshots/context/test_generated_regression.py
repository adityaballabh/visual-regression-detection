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
        """Guards the footer contact paragraph color against the heading recolor change.

        The change that set the section headings to #1e40af also set the footer
        "Contact us at" paragraph color to #1e40af, making it unreadable on the blue footer.
        """
        contacts = [
            element for element in self.snapshot.elements if element.tag == "p" and element.own_text == CONTACT_TEXT
        ]
        self.assertEqual(
            len(contacts), 1, f"Expected one footer paragraph with text {CONTACT_TEXT!r}, found {len(contacts)}"
        )
        contact = contacts[0]
        actual = contact.styles["color"]
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{contact.selector}: property 'color' expected {EXPECTED_COLOR} but got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
