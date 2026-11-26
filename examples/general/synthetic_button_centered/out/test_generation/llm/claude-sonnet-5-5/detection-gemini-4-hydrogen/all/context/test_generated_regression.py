import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
LABELS = {
    "Username": f"{FORM} > div:nth-child(1) > label:nth-child(1)",
    "Password": f"{FORM} > div:nth-child(2) > label:nth-child(1)",
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
            if not element.frames and element.selector == selector:
                return element
        self.fail(f"{selector}: element not found in snapshot")

    def test_form_labels_stay_left_aligned(self):
        """Guards the Username and Password form labels staying left-aligned above their inputs.

        Regression caused by the change that centered the Sign Up button: it also added
        `text-align:center` to both label elements in the free trial form.
        """
        for text, selector in LABELS.items():
            label = self.find(selector)
            self.assertEqual(label.own_text.strip(), text, f"{selector}: own_text")
            actual = label.styles.get("text-align")
            self.assertEqual(
                actual,
                EXPECTED_TEXT_ALIGN,
                f"{selector}: text-align expected {EXPECTED_TEXT_ALIGN!r} but got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
