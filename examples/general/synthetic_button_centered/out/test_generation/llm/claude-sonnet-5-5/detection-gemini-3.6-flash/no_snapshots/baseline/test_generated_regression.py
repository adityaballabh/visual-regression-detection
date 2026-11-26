import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FIELD_IDS = ["username", "password"]


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, tag, **attributes):
        for element in self.snapshot.elements:
            if element.tag != tag:
                continue
            if all(element.attributes.get(k) == v for k, v in attributes.items()):
                return element
        self.fail(f"No <{tag}> with attributes {attributes} in the snapshot")

    def test_form_labels_stay_left_aligned_with_inputs(self):
        """Guards the sign up form labels staying left-aligned with their inputs.

        The change that added `text-align:center` to the Username and Password
        labels (while centering the Sign Up button) moved the labels away from
        the left edge of the input boxes.
        """
        for field_id in FIELD_IDS:
            label = self.find("label", **{"for": field_id})
            field = self.find("input", id=field_id)
            selector = label.selector

            text_align = label.styles.get("text-align")
            self.assertIn(
                text_align,
                ("start", "left"),
                f"{selector}: property text-align expected 'start' or 'left', actual {text_align!r}",
            )

            text_x = label.text_box.x1 if label.text_box else label.box.x1
            self.assertLessEqual(
                abs(text_x - field.box.x1),
                1 + 12,
                f"{selector}: label text x expected near input left edge {field.box.x1} "
                f"({field.selector}), actual {text_x}",
            )
