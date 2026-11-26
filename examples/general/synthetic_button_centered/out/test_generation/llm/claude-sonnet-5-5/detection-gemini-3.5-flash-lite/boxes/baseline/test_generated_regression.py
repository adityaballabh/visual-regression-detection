import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABELS = [
    (f"{FORM_SELECTOR} > div:nth-child(1) > label:nth-child(1)", "Username"),
    (f"{FORM_SELECTOR} > div:nth-child(2) > label:nth-child(1)", "Password"),
]
LEFT_ALIGNED = ("start", "left")


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, selector):
        for element in self.snapshot.elements:
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_form_labels_are_left_aligned(self):
        """Guards the free trial form labels staying left-aligned.

        The regression came from adding `text-align:center` to the inline style of the
        Username and Password labels in after.html, which centered their text.
        """
        for selector, text in LABELS:
            label = self.find(selector)
            self.assertEqual(
                label.own_text, text, f"{selector}: property own_text expected {text!r}, got {label.own_text!r}"
            )
            actual = label.styles.get("text-align")
            self.assertIn(
                actual,
                LEFT_ALIGNED,
                f"{selector}: property text-align expected 'start', got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
