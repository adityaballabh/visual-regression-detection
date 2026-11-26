import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Left edge offsets in the before snapshot are 0 for labels and the button, allow 1 px
TOLERANCE = 1


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def find(self, tag, text=None):
        for element in self.snapshot.elements:
            if element.tag == tag and (text is None or element.own_text == text):
                return element
        self.fail(f"No <{tag}> element with text {text!r} in the snapshot")

    def test_sign_up_form_is_left_aligned(self):
        """Guards the Sign Up card form staying left-aligned.

        The change that broke it added `text-align:center` to the Username and Password labels
        and `display:block;margin:0 auto` to the Sign Up button, which centered them in the form.
        """
        form = self.find("form")
        for text in ("Username", "Password"):
            label = self.find("label", text)
            self.assertIsNotNone(label.text_box, f"{label.selector}: label has no text box")
            offset = label.text_box.x1 - form.box.x1 - self.padding_left(form)
            self.assertLessEqual(
                abs(offset),
                TOLERANCE,
                f"{label.selector} text left offset from the form content edge: expected 0, got {offset}",
            )
            self.assertNotEqual(
                label.styles.get("text-align"),
                "center",
                f"{label.selector} text-align: expected start/left, got center",
            )

        button = self.find("button", "Sign Up")
        offset = button.box.x1 - form.box.x1 - self.padding_left(form)
        self.assertLessEqual(
            abs(offset),
            TOLERANCE,
            f"{button.selector} left offset from the form content edge: expected 0, got {offset}",
        )

    @staticmethod
    def padding_left(form):
        return round(float(form.styles["padding-left"].removesuffix("px")))


if __name__ == "__main__":
    unittest.main()
