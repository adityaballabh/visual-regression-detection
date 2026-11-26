import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
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

        Regression caused by the change that recolored the section headings to #1e40af, which
        also changed the footer contact paragraph's inline color from white to #1e40af.
        """
        matches = []
        for element in self.snapshot.elements:
            if element.selector == SELECTOR and not element.frames:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected one element, found {len(matches)}")
        actual = matches[0].styles["color"]
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{SELECTOR}: property 'color' expected {EXPECTED_COLOR} but was {actual}",
        )


if __name__ == "__main__":
    unittest.main()
