import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
FRAMES = []
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_is_white(self):
        """Guards the footer contact text color against the heading recolor change.

        The headings were changed from #222 to #1e40af in the page, and the footer
        contact paragraph's inline style changed from color:white to color:#1e40af,
        which made the text dark blue on the bright blue footer.
        """
        matches = [e for e in self.snapshot.elements if e.selector == SELECTOR and list(e.frames) == FRAMES]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: element not found in snapshot")
        element = matches[0]
        actual = element.styles.get("color")
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{SELECTOR}: property 'color' expected {EXPECTED_COLOR} but got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
