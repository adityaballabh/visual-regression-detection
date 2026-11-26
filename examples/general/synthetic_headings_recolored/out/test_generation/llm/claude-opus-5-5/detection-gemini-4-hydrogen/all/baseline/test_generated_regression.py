import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
# Contact text color in the before snapshot, white on the blue footer
CONTACT_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_element(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element missing from snapshot")

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line staying white on the blue footer.

        The heading recolor in after.html also changed the inline style of the
        footer contact <p> from color:white to color:#1e40af, leaving dark blue
        text on the #3b82f6 footer background.
        """
        contact = self.find_element(CONTACT_SELECTOR)
        color = contact.styles.get("color")
        self.assertEqual(
            color,
            CONTACT_COLOR,
            f"{CONTACT_SELECTOR}: color expected {CONTACT_COLOR}, got {color}",
        )


if __name__ == "__main__":
    unittest.main()
