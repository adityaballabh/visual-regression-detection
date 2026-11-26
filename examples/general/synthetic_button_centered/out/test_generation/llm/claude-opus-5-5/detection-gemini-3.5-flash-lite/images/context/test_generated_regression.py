import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FORM = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2)"
USERNAME_LABEL = f"{FORM} > div:nth-child(1) > label:nth-child(1)"
PASSWORD_LABEL = f"{FORM} > div:nth-child(2) > label:nth-child(1)"
SIGN_UP_BUTTON = f"{FORM} > button:nth-child(3)"


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
        self.fail(f"{selector}: element missing from snapshot")

    def assert_style(self, selector, name, expected):
        actual = self.find(selector).styles.get(name)
        self.assertEqual(actual, expected, f"{selector}: {name} expected {expected!r}, got {actual!r}")

    def test_form_labels_and_sign_up_button_keep_start_alignment(self):
        """Guards the free trial form labels and Sign Up button against moving off the left edge.

        Caused by the form markup change that added text-align:center to the Username and
        Password labels and display:block;margin:0 auto to the Sign Up button.
        """
        self.assert_style(USERNAME_LABEL, "text-align", "start")
        self.assert_style(PASSWORD_LABEL, "text-align", "start")
        self.assert_style(SIGN_UP_BUTTON, "display", "inline-block")
        self.assert_style(SIGN_UP_BUTTON, "margin-left", "0px")
        self.assert_style(SIGN_UP_BUTTON, "margin-right", "0px")
        x1 = self.find(SIGN_UP_BUTTON).box.x1
        self.assertLessEqual(abs(x1 - 56), 1, f"{SIGN_UP_BUTTON}: box x1 expected 56, got {x1}")


if __name__ == "__main__":
    unittest.main()
