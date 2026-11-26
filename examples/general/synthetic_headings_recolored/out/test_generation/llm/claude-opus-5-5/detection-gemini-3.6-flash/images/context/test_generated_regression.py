import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
# Footer contact text is white on the blue footer in the before snapshot
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
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"{selector}: element missing from snapshot")

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact line keeping its white text on the blue footer.

        The heading recolor changed the contact <p> inline style from color:white to
        color:#1e40af, making it dark blue on the blue footer background.
        """
        contact = self.find_element(CONTACT_SELECTOR)
        actual = contact.styles["color"]
        self.assertEqual(
            actual,
            CONTACT_COLOR,
            f"{CONTACT_SELECTOR}: color expected {CONTACT_COLOR}, got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
