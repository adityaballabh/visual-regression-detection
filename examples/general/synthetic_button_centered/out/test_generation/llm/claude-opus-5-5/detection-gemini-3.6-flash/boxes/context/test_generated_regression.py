import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
USERNAME_LABEL = f"{FORM} > div:nth-child(1) > label:nth-child(1)"
PASSWORD_LABEL = f"{FORM} > div:nth-child(2) > label:nth-child(1)"
# Labels sit at the start of their row in the before snapshot
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
        self.fail(f"{selector}: element missing from snapshot")

    def test_form_labels_stay_start_aligned(self):
        """Guards the Username and Password labels of the free trial form against being centered.

        Centering the Sign Up button also added text-align:center to the inline style of both
        labels in the #trial form, so they no longer line up with the start of their inputs.
        """
        for selector in (USERNAME_LABEL, PASSWORD_LABEL):
            label = self.find(selector)
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector} ('{label.own_text}'): text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
