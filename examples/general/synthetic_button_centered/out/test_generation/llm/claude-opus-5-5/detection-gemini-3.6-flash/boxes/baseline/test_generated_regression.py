import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Label selectors and their computed text-align in the before snapshot
EXPECTED_TEXT_ALIGN = {
    "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(1) > label:nth-child(1)": "start",
    "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > form:nth-child(2) > div:nth-child(2) > label:nth-child(1)": "start",
}


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
        """Guards the Username and Password labels of the free trial form against turning center aligned.

        The change that centered the Sign Up button also added text-align:center to the inline
        style of both labels in the trial section form.
        """
        for selector, expected in EXPECTED_TEXT_ALIGN.items():
            with self.subTest(selector=selector):
                actual = self.find_element(selector).styles.get("text-align")
                self.assertEqual(
                    actual,
                    expected,
                    f"{selector}: text-align expected {expected!r}, got {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
