import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM_PATH = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABELS = [
    (f"{FORM_PATH} > div:nth-child(1) > label:nth-child(1)", "Username"),
    (f"{FORM_PATH} > div:nth-child(2) > label:nth-child(1)", "Password"),
]
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
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_form_labels_stay_start_aligned(self):
        """Guards the form labels staying start aligned.

        Regression: centering the 'Sign Up' button in the free trial form also added
        `text-align:center` to the 'Username' and 'Password' label inline styles.
        """
        for selector, text in LABELS:
            with self.subTest(label=text):
                label = self.find(selector)
                self.assertEqual(label.own_text, text, f"{selector}: own_text")
                actual = label.styles.get("text-align")
                self.assertEqual(
                    actual,
                    EXPECTED_TEXT_ALIGN,
                    f"{selector}: text-align expected {EXPECTED_TEXT_ALIGN!r} but was {actual!r}",
                )
