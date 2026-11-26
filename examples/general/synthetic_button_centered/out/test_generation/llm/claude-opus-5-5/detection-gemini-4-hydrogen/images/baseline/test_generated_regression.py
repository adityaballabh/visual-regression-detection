import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Label text alignment taken from the before snapshot
EXPECTED_TEXT_ALIGN = "start"
LABEL_TARGETS = ["username", "password"]


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_label(self, target):
        for element in self.snapshot.elements:
            if not element.frames and element.tag == "label" and element.attributes.get("for") == target:
                return element
        self.fail(f"label[for={target}] is missing from the snapshot")

    def test_sign_up_labels_stay_left_aligned(self):
        """Guards the Sign Up form labels against becoming centered.

        The change that centered the Sign Up button also added text-align:center to the
        Username and Password labels, so they no longer line up with the heading and inputs.
        The button centering is intended and is not checked here.
        """
        for target in LABEL_TARGETS:
            label = self.find_label(target)
            actual = label.styles.get("text-align")
            with self.subTest(label=label.selector):
                self.assertEqual(
                    actual,
                    EXPECTED_TEXT_ALIGN,
                    f"{label.selector}: text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
