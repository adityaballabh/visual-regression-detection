import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_contact_paragraph_stays_white(self):
        """Guards the footer contact paragraph staying white on the blue footer.

        The heading recolor to #1e40af also changed the inline style of the footer
        contact paragraph from color:white to color:#1e40af, making it dark blue.
        """
        matches = [
            element for element in self.snapshot.elements if element.selector == CONTACT_SELECTOR and not element.frames
        ]
        self.assertTrue(matches, f"{CONTACT_SELECTOR}: element not found")
        actual = matches[0].styles.get("color")
        expected = "rgb(255, 255, 255)"
        self.assertEqual(
            actual,
            expected,
            f"{CONTACT_SELECTOR}: property color expected {expected} but was {actual}",
        )


if __name__ == "__main__":
    unittest.main()
