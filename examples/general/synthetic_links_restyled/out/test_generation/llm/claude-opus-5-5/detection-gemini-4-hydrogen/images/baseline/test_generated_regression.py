import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

NAV = "html:nth-child(1) > body:nth-child(2) > header:nth-child(1) > nav:nth-child(2)"

# Left edge of each header link in the before snapshot
EXPECTED_LEFT_EDGES = {
    f"{NAV} > a:nth-child(1)": 967,
    f"{NAV} > a:nth-child(2)": 1034,
    f"{NAV} > a:nth-child(3)": 1100,
    f"{NAV} > a:nth-child(4)": 1185,
}


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_nav_links_keep_their_position(self):
        """Guards the header nav links (Home, About, Services, Contact) against shifting left.

        The shift came from the inline style change in before.html -> after.html that added
        font-weight:bold to each nav <a>, widening the links in the right-aligned nav.
        """
        elements_by_selector = {}
        for element in self.snapshot.elements:
            if not element.frames:
                elements_by_selector[element.selector] = element
        for selector, expected_x1 in EXPECTED_LEFT_EDGES.items():
            element = elements_by_selector.get(selector)
            self.assertIsNotNone(element, f"{selector}: element missing from snapshot")
            actual_x1 = element.box.x1
            self.assertLessEqual(
                abs(actual_x1 - expected_x1),
                1,
                f"{selector}: box x1 expected {expected_x1}, got {actual_x1}",
            )


if __name__ == "__main__":
    unittest.main()
