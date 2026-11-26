import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

LABEL_SELECTORS = {
    "Username": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)",
    "Password": "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)",
}
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

    def test_form_labels_keep_default_text_alignment(self):
        """Guards the free trial form labels (Username, Password) keeping their default text-align.

        The change that added `text-align:center` to the label inline styles, alongside centering the
        Sign Up button with `display:block;margin:0 auto`, wrongly centered the labels too.
        """
        for text, selector in LABEL_SELECTORS.items():
            label = self.find(selector)
            self.assertEqual(label.own_text, text, f"{selector}: own_text expected {text!r}, got {label.own_text!r}")
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector}: text-align expected {EXPECTED_TEXT_ALIGN!r}, got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
