import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Computed background of the Courses card header in the BEFORE snapshot (Bootstrap bg-primary)
EXPECTED_BACKGROUND = "rgb(13, 110, 253)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_courses_card_header_is_primary(self):
        """Guards the Courses card header on the administrator courses page staying primary blue.

        Caused by administratorCourses.html.tsx changing the header class from `bg-primary` to
        `bg-secondary`, which turned the header background dark grey.
        """
        elements = {element.id: element for element in self.snapshot.elements}
        headers = []
        for element in self.snapshot.elements:
            parent = elements.get(element.parent)
            if (
                parent is not None
                and parent.attributes.get("id") == "courses"
                and "card-header" in element.attributes.get("class", "").split()
            ):
                headers.append(element)
        self.assertEqual(len(headers), 1, "Expected one card-header inside #courses")
        header = headers[0]
        actual = header.styles["background-color"]
        self.assertEqual(
            actual,
            EXPECTED_BACKGROUND,
            f"{header.selector}: background-color expected {EXPECTED_BACKGROUND}, got {actual}",
        )
