import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
# White, the footer text color in the before snapshot
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_contact_paragraph(self):
        for element in self.snapshot.elements:
            if element.tag == "p" and element.own_text.strip() == CONTACT_TEXT:
                return element
        self.fail(f"No <p> with text {CONTACT_TEXT!r} in the snapshot")

    def test_footer_contact_text_stays_white(self):
        """Guards box 4: the footer contact line must stay white on the blue footer.

        The change that recolored the section headings to #1e40af also set the footer's
        "Contact us at" paragraph to color:#1e40af, making it dark blue on the #3b82f6 background.
        """
        contact = self.find_contact_paragraph()
        actual = contact.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{contact.selector}: color expected {EXPECTED_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
