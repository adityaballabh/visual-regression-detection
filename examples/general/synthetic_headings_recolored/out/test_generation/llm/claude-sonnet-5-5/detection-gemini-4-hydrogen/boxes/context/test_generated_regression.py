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
        """Guards the footer contact paragraph staying white on the blue footer.

        The heading recolor changed the inline style of the footer's last <p> from
        color:white to color:#1e40af, which was not part of the intended heading change.
        """
        matches = [e for e in self.snapshot.elements if e.selector == SELECTOR and not e.frames]
        self.assertEqual(len(matches), 1, f"{SELECTOR}: element not found in snapshot")
        actual = matches[0].styles["color"]
        self.assertEqual(
            actual,
            EXPECTED_COLOR,
            f"{SELECTOR}: property 'color' expected {EXPECTED_COLOR} but got {actual}",
        )


if __name__ == "__main__":
    unittest.main()
