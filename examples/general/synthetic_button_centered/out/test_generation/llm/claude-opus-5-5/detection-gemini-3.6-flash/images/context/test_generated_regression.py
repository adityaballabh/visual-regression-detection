import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Text alignment of each form label in the before snapshot, keyed by its `for` attribute
EXPECTED_TEXT_ALIGN = {"username": "start", "password": "start"}


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, field_id):
        for element in self.snapshot.elements:
            if not element.frames and element.tag == "label" and element.attributes.get("for") == field_id:
                return element
        self.fail(f"label[for={field_id}] is missing from the snapshot")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password labels of the free trial form against becoming centered.

        Centering the Sign Up button also added text-align:center to both label styles in the form.
        """
        for field_id, expected in EXPECTED_TEXT_ALIGN.items():
            label = self.find_label(field_id)
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                expected,
                f"{label.selector} (label[for={field_id}]): text-align expected {expected!r}, got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
