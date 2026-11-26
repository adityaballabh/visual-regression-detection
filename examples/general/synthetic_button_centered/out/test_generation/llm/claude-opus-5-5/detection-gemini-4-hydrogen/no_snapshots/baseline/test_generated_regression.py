import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Expected values from the before snapshot
EXPECTED_TEXT_ALIGN = "start"
# Label text starts at the label's left edge when left aligned
EXPECTED_TEXT_OFFSET = 0


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, input_id):
        for element in self.snapshot.elements:
            if element.tag == "label" and element.attributes.get("for") == input_id:
                return element
        self.fail(f'label[for="{input_id}"] is missing')

    def test_sign_up_labels_stay_left_aligned(self):
        """Guards the Username and Password labels in the Sign Up form against being centered.

        The change meant to center only the Sign Up button also added `text-align:center` to both
        labels in the trial form, moving them away from the left-aligned heading and inputs.
        """
        for input_id in ("username", "password"):
            label = self.find_label(input_id)
            with self.subTest(selector=label.selector):
                text_align = label.styles.get("text-align")
                self.assertEqual(
                    text_align,
                    EXPECTED_TEXT_ALIGN,
                    f"{label.selector} text-align: expected {EXPECTED_TEXT_ALIGN!r}, got {text_align!r}",
                )
                text_offset = label.text_box.x1 - label.box.x1
                self.assertLessEqual(
                    abs(text_offset - EXPECTED_TEXT_OFFSET),
                    1,
                    f"{label.selector} text left offset: expected {EXPECTED_TEXT_OFFSET}px, got {text_offset}px",
                )


if __name__ == "__main__":
    unittest.main()
