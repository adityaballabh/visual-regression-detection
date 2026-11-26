import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Form labels flagged by the detector, keyed by their stable for attribute
LABEL_FOR_IDS = ["username", "password"]
# Computed text-align of both labels in the before snapshot
EXPECTED_TEXT_ALIGN = "start"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, for_id):
        for element in self.snapshot.elements:
            if not element.frames and element.tag == "label" and element.attributes.get("for") == for_id:
                return element
        self.fail(f"label[for={for_id}] is missing from the snapshot")

    def test_form_labels_stay_start_aligned(self):
        """Guards the free trial form's Username and Password labels against being centered.

        The change meant to center only the Sign Up button, but it also added
        text-align:center to the inline style of both form labels.
        """
        for for_id in LABEL_FOR_IDS:
            label = self.find_label(for_id)
            actual = label.styles.get("text-align")
            with self.subTest(label=for_id):
                self.assertEqual(
                    actual,
                    EXPECTED_TEXT_ALIGN,
                    f"{label.selector}: text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
