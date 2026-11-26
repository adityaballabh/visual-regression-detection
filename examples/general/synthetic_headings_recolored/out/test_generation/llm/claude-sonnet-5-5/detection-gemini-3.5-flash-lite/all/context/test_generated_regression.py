import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FOOTER_EMAIL_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_email_stays_white(self):
        """Guards the footer contact email color, which was wrongly turned dark blue.

        The change that recolored the section headings to #1e40af also set the footer
        paragraph "Contact us at: info@educationalinstitute.com" to color:#1e40af,
        making it unreadable on the blue footer.
        """
        matches = []
        for element in self.snapshot.elements:
            if not element.frames and element.selector == FOOTER_EMAIL_SELECTOR:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{FOOTER_EMAIL_SELECTOR}: element not found")
        styles = matches[0].styles
        for prop in ("color", "-webkit-text-fill-color"):
            self.assertEqual(
                styles.get(prop),
                EXPECTED_COLOR,
                f"{FOOTER_EMAIL_SELECTOR}: {prop} expected {EXPECTED_COLOR}, got {styles.get(prop)}",
            )


if __name__ == "__main__":
    unittest.main()
