import unittest

from image_diff.model import Snapshot
from image_diff.tests.fixtures import element


class SnapshotTests(unittest.TestCase):
    def test_label_fallbacks(self):
        snapshot = Snapshot(
            (
                element(0, None, tag="section"),
                element(
                    1, 0, tag="p", own_text="Join our team of dedicated volunteers and make a difference in the world."
                ),
                element(2, None, tag="button", own_text="Sign up", attributes={"id": "cta"}),
                element(3, None, tag="nav", attributes={"aria-label": "Main"}),
                element(4, None, tag="img", attributes={"src": "/static/logo.png"}),
                element(5, None),
            )
        )
        self.assertEqual(
            [snapshot.label(element) for element in snapshot.elements],
            [
                "<section> containing 'Join our team of dedicated volunteers an...'",
                "<p> 'Join our team of dedicated volunteers an...'",
                "<button id=\"cta\"> 'Sign up'",
                '<nav aria-label="Main">',
                "<img> 'logo.png'",
                "<div>",
            ],
        )


if __name__ == "__main__":
    unittest.main()
