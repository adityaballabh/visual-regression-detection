import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
# Computed color of the contact line in the before snapshot
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_contact_line(self):
        for element in self.snapshot.elements:
            if element.tag == "p" and element.own_text.strip() == CONTACT_TEXT:
                return element
        self.fail(f"No <p> with text {CONTACT_TEXT!r} in the snapshot")

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line against losing its white text on the blue footer.

        The heading recolor in after.html also changed the footer <p> inline color from white to
        #1e40af, leaving dark blue text on the #3b82f6 footer background.
        """
        contact_line = self.find_contact_line()
        actual = contact_line.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{contact_line.selector} color: expected {EXPECTED_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
