import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

LABEL_SELECTORS = {
    "Username": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)",
    "Password": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)",
}

# Computed text-align of the form labels in the BEFORE snapshot
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
        self.fail(f"Element not found: {selector}")

    def test_form_labels_stay_left_aligned(self):
        """Guards against the form labels becoming centered.

        Centering the Sign Up button added `text-align:center` to the 'Username' and 'Password' labels
        in after.html, so they no longer align with their left-aligned inputs.
        """
        for text, selector in LABEL_SELECTORS.items():
            label = self.find(selector)
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector} ({text!r}): property text-align expected {EXPECTED_TEXT_ALIGN!r} but was {actual!r}",
            )
