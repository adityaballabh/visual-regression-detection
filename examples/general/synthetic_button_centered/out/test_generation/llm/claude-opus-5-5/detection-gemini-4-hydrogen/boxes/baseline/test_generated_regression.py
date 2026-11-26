import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABELS = {
    "Username": f"{FORM} > div:nth-child(1) > label:nth-child(1)",
    "Password": f"{FORM} > div:nth-child(2) > label:nth-child(1)",
}


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if element.frames == () and element.selector == selector:
                return element
        self.fail(f"{selector}: element missing")

    def test_form_labels_stay_start_aligned(self):
        """Guards the Username and Password labels of the free trial form against turning centered.

        The change that centered the Sign Up button also added text-align:center to both
        label inline styles, the button centering itself is intended and not checked here.
        """
        for text, selector in LABELS.items():
            label = self.find(selector)
            self.assertEqual(label.own_text, text, f"{selector}: own_text expected {text!r}, got {label.own_text!r}")
            actual = label.styles.get("text-align")
            self.assertEqual(actual, "start", f"{selector}: text-align expected 'start', got {actual!r}")


if __name__ == "__main__":
    unittest.main()
