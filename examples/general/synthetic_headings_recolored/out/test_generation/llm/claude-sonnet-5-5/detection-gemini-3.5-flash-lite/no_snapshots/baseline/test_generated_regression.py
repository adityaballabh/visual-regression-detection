import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

HEADINGS = ["Academic Programs", "Faculty", "Faculty Research"]
EXPECTED_COLOR = "rgb(34, 34, 34)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_section_headings_keep_dark_text_color(self):
        """Guards against section headings turning blue (#222 -> #1e40af on the h2 elements in the
        programs, faculty and research sections of the page)."""
        headings = {}
        for element in self.snapshot.elements:
            if element.tag == "h2":
                headings[element.own_text.strip()] = element
        for text in HEADINGS:
            self.assertIn(text, headings, f"h2 with text {text!r} is missing")
            element = headings[text]
            actual = element.styles.get("color")
            self.assertEqual(
                actual,
                EXPECTED_COLOR,
                f"{element.selector} (h2 {text!r}): property color expected {EXPECTED_COLOR}, got {actual}",
            )
