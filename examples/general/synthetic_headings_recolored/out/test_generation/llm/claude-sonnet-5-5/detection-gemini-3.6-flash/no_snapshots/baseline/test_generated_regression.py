import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_TEXT = "Contact us at: info@educationalinstitute.com"
EXPECTED_COLOR = "rgb(255, 255, 255)"
EXPECTED_BACKGROUND = "rgb(59, 130, 246)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_is_readable(self):
        """Guards the footer contact line "Contact us at: info@educationalinstitute.com".

        The change that caused the regression set its inline color from white to #1e40af,
        which is dark blue on the footer's #3b82f6 blue background and almost unreadable.
        """
        contact = None
        for element in self.snapshot.elements:
            if element.tag == "p" and element.own_text.strip() == CONTACT_TEXT:
                contact = element
        self.assertIsNotNone(contact, f"No <p> with text {CONTACT_TEXT!r} found in the snapshot")

        color = contact.styles["color"]
        self.assertEqual(
            color,
            EXPECTED_COLOR,
            f"{contact.selector}: property 'color' expected {EXPECTED_COLOR} but was {color}",
        )

        footer = self.snapshot.elements[0]
        for element in self.snapshot.elements:
            if element.id == contact.parent or element is contact.parent:
                footer = element
        background = footer.styles["background-color"]
        self.assertEqual(
            background,
            EXPECTED_BACKGROUND,
            f"{footer.selector}: property 'background-color' expected {EXPECTED_BACKGROUND} but was {background}",
        )
