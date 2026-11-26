import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

LABEL_SELECTORS = [
    "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)",
    "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)",
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
            if element.selector == selector and not element.frames:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_sign_up_form_labels_stay_left_aligned(self):
        """Guards against the Sign Up form labels being centered.

        The change added `text-align:center` to the inline style of the Username and Password
        labels in the free trial form, so they no longer line up with the left-aligned inputs.
        """
        for selector in LABEL_SELECTORS:
            label = self.find(selector)
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector}: property text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
