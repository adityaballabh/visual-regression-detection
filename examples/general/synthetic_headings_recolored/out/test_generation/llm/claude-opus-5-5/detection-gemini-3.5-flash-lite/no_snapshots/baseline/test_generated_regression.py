import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

# Inline color #222 on each section heading in the before page
HEADING_COLOR = "rgb(34, 34, 34)"
SECTION_IDS = ("programs", "faculty", "research")


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def heading_in_section(self, section_id):
        for element in self.snapshot.elements:
            if element.tag == "h2" and element.parent is not None:
                parent = self.snapshot.elements[element.parent]
                if parent.attributes.get("id") == section_id:
                    return element
        self.fail(f"No h2 inside section#{section_id}")

    def test_section_headings_keep_dark_gray_color(self):
        """Guards the section headings 'Academic Programs', 'Faculty' and 'Faculty Research' turning
        from #222 to link blue, caused by the h2 inline color changing to #1e40af in the main sections."""
        for section_id in SECTION_IDS:
            heading = self.heading_in_section(section_id)
            color = heading.styles.get("color")
            with self.subTest(section=section_id):
                self.assertEqual(
                    color,
                    HEADING_COLOR,
                    f"{heading.selector} color: expected {HEADING_COLOR}, got {color}",
                )


if __name__ == "__main__":
    unittest.main()
