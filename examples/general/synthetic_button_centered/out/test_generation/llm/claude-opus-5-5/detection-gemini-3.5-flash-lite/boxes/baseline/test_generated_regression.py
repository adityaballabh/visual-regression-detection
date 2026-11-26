import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
USERNAME_LABEL = f"{FORM} > div:nth-child(1) > label:nth-child(1)"
PASSWORD_LABEL = f"{FORM} > div:nth-child(2) > label:nth-child(1)"
# Computed text-align of both labels in the before snapshot
LABEL_TEXT_ALIGN = "start"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find_element(self, selector):
        for element in self.snapshot.elements:
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element missing from snapshot")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password labels of the free trial form staying left-aligned.

        The change that centered the Sign Up button also added text-align:center to the
        inline style of both labels in the trial form. The button centering is intended, so
        only the labels are checked.
        """
        for selector in (USERNAME_LABEL, PASSWORD_LABEL):
            text_align = self.find_element(selector).styles.get("text-align")
            self.assertEqual(
                text_align,
                LABEL_TEXT_ALIGN,
                f"{selector}: text-align expected {LABEL_TEXT_ALIGN!r}, got {text_align!r}",
            )


if __name__ == "__main__":
    unittest.main()
