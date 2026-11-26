import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, tag, **attributes):
        for element in self.snapshot.elements:
            if element.tag != tag or element.frames:
                continue
            if all(element.attributes.get(k) == v for k, v in attributes.items()):
                return element
        self.fail(f"No <{tag}> with attributes {attributes} in the snapshot")

    def test_form_labels_stay_left_aligned_with_their_inputs(self):
        """Guards the Username and Password labels of the free trial form staying left aligned.

        Regression caused by the change that added `text-align:center` to both labels
        (next to the intended centering of the Sign Up button), which moved the label
        text to the middle of the form card, away from the left edge of its input.
        """
        for field in ("username", "password"):
            label = self.find("label", **{"for": field})
            field_input = self.find("input", id=field)
            selector = label.selector

            align = label.styles.get("text-align")
            self.assertIn(
                align,
                ("start", "left"),
                f"{selector} (label for {field}): text-align expected 'start' but got {align!r}",
            )

            text_box = label.text_box
            self.assertIsNotNone(text_box, f"{selector}: label has no rendered text box")
            self.assertLessEqual(
                abs(text_box.x1 - field_input.box.x1),
                1,
                f"{selector} (label for {field}): text left edge x1 expected {field_input.box.x1} "
                f"(the input's left edge) but got {text_box.x1}",
            )


if __name__ == "__main__":
    unittest.main()
