import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

HEADER_SELECTOR = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(2) > "
    "div:nth-child(1) > main:nth-child(1) > div:nth-child(1) > div:nth-child(5) > "
    "div:nth-child(1) > div:nth-child(1)"
)
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_courses_card_header_is_primary_blue(self):
        """Guards the Courses card header color in the student courses card.

        The change swapped the header class from `bg-primary` to `bg-secondary`, which turned
        the background from blue to dark gray and broke consistency with the Development Mode panel.
        """
        header = None
        for element in self.snapshot.elements:
            if element.selector == HEADER_SELECTOR and not element.frames:
                header = element
                break
        self.assertIsNotNone(header, f"{HEADER_SELECTOR}: element not found in snapshot")
        actual = header.styles.get("background-color")
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{HEADER_SELECTOR}: background-color expected {EXPECTED_BACKGROUND!r} but got {actual!r}",
        )


if __name__ == "__main__":
    unittest.main()
