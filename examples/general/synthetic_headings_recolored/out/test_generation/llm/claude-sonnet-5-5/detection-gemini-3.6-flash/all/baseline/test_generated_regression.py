import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

FOOTER_CONTACT_SELECTOR = "html:nth-child(1) > body:nth-child(2) > footer:nth-child(3) > p:nth-child(3)"
EXPECTED_TEXT = "Contact us at: info@educationalinstitute.com"
EXPECTED_COLOR = "rgb(255, 255, 255)"


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def test_footer_contact_text_stays_white(self):
        """Guards the footer contact text color on the blue footer.

        The heading color update (#222 -> #1e40af) was also applied to the footer contact
        paragraph (inline color white -> #1e40af), making it unreadable on the blue background.
        """
        matches = []
        for element in self.snapshot.elements:
            if element.selector == FOOTER_CONTACT_SELECTOR and not element.frames:
                matches.append(element)
        self.assertEqual(len(matches), 1, f"{FOOTER_CONTACT_SELECTOR}: expected one element, found {len(matches)}")
        element = matches[0]
        self.assertEqual(element.own_text, EXPECTED_TEXT, f"{FOOTER_CONTACT_SELECTOR}: property own_text")
        for prop in ("color", "-webkit-text-fill-color"):
            actual = element.styles.get(prop)
            self.assertEqual(
                actual,
                EXPECTED_COLOR,
                f"{FOOTER_CONTACT_SELECTOR}: property {prop} expected {EXPECTED_COLOR!r} but got {actual!r}",
            )


if __name__ == "__main__":
    unittest.main()
