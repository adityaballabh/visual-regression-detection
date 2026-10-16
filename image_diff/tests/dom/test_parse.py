import json
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot, parse_snapshot
from image_diff.model import Box, Element, Snapshot

_EXAMPLES = Path(__file__).parents[2] / "examples"
_EXAMPLE = _EXAMPLES / "button_darkened" / "before_snapshot.json"
# Captured from iframe.html
_IFRAME_PAGE = Path(__file__).parent / "iframe_snapshot.json"


def _first(snapshot: Snapshot, tag: str) -> Element:
    return next(element for element in snapshot.elements if element.tag == tag)


class ParseTests(unittest.TestCase):
    def test_example_button_loaded(self):
        snapshot = load_snapshot(_EXAMPLE)
        button = _first(snapshot, "button")

        self.assertEqual(snapshot.label(button), "<button> 'Join Now'")
        self.assertEqual(button.box, Box(16, 128, 99, 168))
        self.assertEqual(button.text_box, Box(24, 139, 91, 157))
        self.assertEqual(
            button.selector, "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"
        )
        self.assertEqual(button.styles["background-color"], "rgb(107, 114, 128)")
        # Comes from same_everywhere
        self.assertEqual(button.styles["box-shadow"], "none")

    def test_boxes_scaled(self):
        capture = json.loads(_EXAMPLE.read_text())
        capture["device_pixel_ratio"] = 2

        snapshot = parse_snapshot(capture)
        button = _first(snapshot, "button")

        self.assertEqual(button.box, Box(32, 256, 198, 336))

    def test_iframe_offset_by_border_and_padding(self):
        snapshot = load_snapshot(_IFRAME_PAGE)
        button = _first(snapshot, "button")

        self.assertEqual(button.box, Box(67, 156, 157, 192))
        self.assertEqual(button.paint_order, 5)
        self.assertEqual(button.frames, ("html:nth-child(1) > body:nth-child(2) > iframe:nth-child(1)",))
        self.assertEqual(button.selector, "html:nth-child(1) > body:nth-child(2) > button:nth-child(1)")

        inner_html = next(element for element in snapshot.elements if element.tag == "html" and element.frames)
        self.assertEqual(snapshot.elements[inner_html.parent].tag, "iframe")


if __name__ == "__main__":
    unittest.main()
