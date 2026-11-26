import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM_LABELS = {
    "Username": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)",
    "Password": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)",
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
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_form_labels_stay_start_aligned(self):
        """Guards the free trial form labels staying start aligned.

        Centering the Sign Up button added `text-align:center` to the Username and
        Password labels in after.html, which centered their text by mistake.
        """
        for text, selector in FORM_LABELS.items():
            with self.subTest(label=text):
                label = self.find(selector)
                actual = label.styles["text-align"]
                self.assertEqual(
                    actual,
                    "start",
                    f"{selector}: property text-align expected 'start' but was '{actual}'",
                )


if __name__ == "__main__":
    unittest.main()
