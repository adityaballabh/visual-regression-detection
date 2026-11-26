import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Text-align and left edge of each label text in the before snapshot
EXPECTED_TEXT_ALIGN = "start"
EXPECTED_TEXT_LEFT = {"username": 56, "password": 56}


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, input_id):
        for element in self.snapshot.elements:
            if not element.frames and element.tag == "label" and element.attributes.get("for") == input_id:
                return element
        self.fail(f"label[for={input_id}] is missing")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password labels against being centered above their left-aligned inputs,
        caused by adding text-align:center to both label styles in the free trial form."""
        for input_id, expected_left in EXPECTED_TEXT_LEFT.items():
            label = self.find_label(input_id)
            text_align = label.styles["text-align"]
            self.assertEqual(
                text_align,
                EXPECTED_TEXT_ALIGN,
                f"{label.selector}: text-align expected {EXPECTED_TEXT_ALIGN!r}, got {text_align!r}",
            )
            text_left = label.text_box.x1
            self.assertAlmostEqual(
                text_left,
                expected_left,
                delta=1,
                msg=f"{label.selector}: text left edge expected {expected_left}, got {text_left}",
            )


if __name__ == "__main__":
    unittest.main()
