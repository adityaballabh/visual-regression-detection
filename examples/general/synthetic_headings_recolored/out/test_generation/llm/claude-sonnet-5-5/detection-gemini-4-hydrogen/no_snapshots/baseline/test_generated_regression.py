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

    def test_footer_contact_text_is_white(self):
        """Guards the footer contact line staying white on the blue footer.

        Changing the section headings to #1e40af also recolored the footer
        paragraph "Contact us at: ..." from white to #1e40af, which is
        unreadable on the #3b82f6 footer background.
        """
        matches = []
        for element in self.snapshot.elements:
            if element.tag.lower() == "p" and CONTACT_TEXT in element.own_text:
                matches.append(element)
        self.assertEqual(
            len(matches),
            1,
            f"p containing '{CONTACT_TEXT}': expected 1 element, found {len(matches)}",
        )
        element = matches[0]
        actual = element.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{element.selector} property 'color': expected {EXPECTED_COLOR}, actual {actual}",
        )


if __name__ == "__main__":
    unittest.main()
