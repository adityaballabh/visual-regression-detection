import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Computed text-align of both labels in the before snapshot
EXPECTED_TEXT_ALIGN = "start"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def label_for(self, input_id):
        for element in self.snapshot.elements:
            if element.tag == "label" and element.attributes.get("for") == input_id:
                return element
        self.fail(f"label[for={input_id}] is missing")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password labels of the free trial form against being centered.

        The change that centered the Sign Up button also added text-align:center to both labels.
        """
        for input_id in ("username", "password"):
            label = self.label_for(input_id)
            text_align = label.styles["text-align"]
            self.assertEqual(
                text_align,
                EXPECTED_TEXT_ALIGN,
                f"{label.selector} text-align: expected {EXPECTED_TEXT_ALIGN!r}, got {text_align!r}",
            )
            # Left aligned text starts at the label's left edge
            text_offset = label.text_box.x1 - label.box.x1
            self.assertLessEqual(
                abs(text_offset),
                1,
                f"{label.selector} text left offset: expected 0 px, got {text_offset} px",
            )


if __name__ == "__main__":
    unittest.main()
