import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Each label is found by the input it names, since the for attribute is the same in both snapshots
LABEL_INPUTS = ("username", "password")


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, input_id):
        for element in self.snapshot.elements:
            if element.frames == () and element.tag == "label" and element.attributes.get("for") == input_id:
                return element
        self.fail(f"No label for #{input_id} in the snapshot")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password labels against being centered.

        Centering the Sign Up button in the free trial form also added text-align:center
        to both labels, moving their text away from the left edge of their inputs.
        """
        for input_id in LABEL_INPUTS:
            with self.subTest(label=input_id):
                label = self.find_label(input_id)
                text_align = label.styles["text-align"]
                self.assertEqual(
                    text_align,
                    "start",
                    f"{label.selector}: text-align expected 'start', got '{text_align}'",
                )
                # Left aligned text starts at the label's own left edge
                self.assertLessEqual(
                    abs(label.text_box.x1 - label.box.x1),
                    1,
                    f"{label.selector}: text left expected {label.box.x1}, got {label.text_box.x1}",
                )


if __name__ == "__main__":
    unittest.main()
