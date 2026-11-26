import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABELS = {
    f"{FORM} > div:nth-child(1) > label:nth-child(1)": "Username",
    f"{FORM} > div:nth-child(2) > label:nth-child(1)": "Password",
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
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"Element {selector} not found in the snapshot")

    def test_form_labels_are_left_aligned(self):
        """Guards the 'Username' and 'Password' form labels staying left-aligned.

        The change that broke them added `text-align:center` to the inline style of both
        <label> elements in the free trial form (before.html -> after.html).
        """
        for selector, text in LABELS.items():
            label = self.find(selector)
            self.assertEqual(label.own_text, text, f"{selector}: own_text")
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                "start",
                f"{selector}: text-align expected 'start' but was '{actual}'",
            )


if __name__ == "__main__":
    unittest.main()
