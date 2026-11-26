import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

NAV_SELECTOR = "html:nth-child(1) > body:nth-child(2) > header:nth-child(1) > nav:nth-child(2)"
NAV_LINKS = [
    (f"{NAV_SELECTOR} > a:nth-child(1)", "Home"),
    (f"{NAV_SELECTOR} > a:nth-child(2)", "About"),
    (f"{NAV_SELECTOR} > a:nth-child(3)", "Services"),
    (f"{NAV_SELECTOR} > a:nth-child(4)", "Contact"),
]
EXPECTED_STYLES = {
    "color": "rgb(31, 41, 55)",
    "font-weight": "400",
}


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
        self.fail(f"{selector}: element not found in snapshot")

    def test_header_nav_links_keep_default_text_style(self):
        """Guards the header nav links keeping dark gray regular-weight text.

        The change that broke it replaced the inline style "padding:4px 8px;color:#1f2937" on each
        nav <a> with "padding:4px 8px;color:#4f46e5;font-weight:bold" in after.html.
        """
        for selector, text in NAV_LINKS:
            element = self.find(selector)
            self.assertEqual(element.tag, "a", f"{selector}: tag")
            self.assertEqual(element.own_text, text, f"{selector}: own_text")
            for prop, expected in EXPECTED_STYLES.items():
                actual = element.styles.get(prop)
                self.assertEqual(
                    actual,
                    expected,
                    f"{selector} ({text}): style '{prop}' expected {expected!r} but was {actual!r}",
                )


if __name__ == "__main__":
    unittest.main()
