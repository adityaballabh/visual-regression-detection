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

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact paragraph against turning dark blue on the blue footer.

        The change that recolored the section headings to dark blue (#1e40af) also changed the
        inline style of the footer contact <p> from color:white to color:#1e40af.
        """
        matches = [e for e in self.snapshot.elements if e.selector == SELECTOR and not e.frames]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: expected one element, found {len(matches)}")
        element = matches[0]
        actual = element.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{SELECTOR}: property color expected {EXPECTED_COLOR}, actual {actual}",
        )
