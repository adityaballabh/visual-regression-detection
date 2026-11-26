import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

LABELLED_INPUTS = ("username", "password")
LEFT_ALIGNED = ("start", "left")


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, tag, **attributes):
        for element in self.snapshot.elements:
            if element.tag == tag and all(element.attributes.get(k) == v for k, v in attributes.items()):
                return element
        self.fail(f"No <{tag}> with attributes {attributes} in the snapshot")

    def test_form_labels_stay_left_aligned(self):
        """Guards the 'Username' and 'Password' labels of the free trial form staying left-aligned above their inputs.

        Caused by the change that added `text-align:center` to both labels while centering the 'Sign Up' button.
        """
        for field in LABELLED_INPUTS:
            label = self.find("label", **{"for": field})
            field_input = self.find("input", id=field)
            selector = label.selector

            align = label.styles["text-align"]
            self.assertIn(
                align,
                LEFT_ALIGNED,
                f"{selector} property text-align: expected one of {LEFT_ALIGNED}, actual {align!r}",
            )

            self.assertLessEqual(
                abs(label.text_box.x1 - field_input.box.x1),
                1,
                f"{selector} property text left edge: expected {field_input.box.x1} (left edge of {field_input.selector}), "
                f"actual {label.text_box.x1}",
            )


if __name__ == "__main__":
    unittest.main()
