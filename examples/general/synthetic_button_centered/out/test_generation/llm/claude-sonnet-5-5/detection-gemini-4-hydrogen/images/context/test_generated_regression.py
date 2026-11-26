import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM_LABELS = {
    "Username": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)",
    "Password": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)",
}
# Value of text-align on the labels in the before snapshot
EXPECTED_TEXT_ALIGN = "start"


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
        """Guards against the Username and Password labels of the free trial form being centered.

        Caused by the change that added `text-align:center` to both <label> elements
        while centering the Sign Up button.
        """
        for text, selector in FORM_LABELS.items():
            label = self.find(selector)
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector} ('{text}'): property text-align expected {EXPECTED_TEXT_ALIGN!r} but was {actual!r}",
            )
