import unittest

from image_diff.dom.paint import explain_paint
from image_diff.model import Box, Kind, Snapshot
from image_diff.tests.fixtures import BUTTON, PAGE, element, snapshot

_GRAY = "rgb(107, 114, 128)"
_BLUE = "rgb(37, 99, 235)"
_BLACK = "rgb(0, 0, 0)"
_WHITE = "rgb(255, 255, 255)"


def _button_page(text: str, styles: dict[str, str]) -> Snapshot:
    return snapshot(
        element(0, None, "body", box=PAGE),
        element(1, 0, "h2", "Settings", box=Box(120, 40, 360, 72)),
        element(2, 0, "button", text, {"class": "btn btn-primary"}, BUTTON, styles),
    )


class PaintTests(unittest.TestCase):
    def test_background_change_explained(self):
        before = _button_page("Save", {"background-color": _GRAY})
        after = _button_page("Save", {"background-color": _BLUE})
        changes, unexplained_shape, unexplained_color = explain_paint([], [BUTTON], before, after)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, Kind.COLOR)
        self.assertEqual(changes[0].element, "<button> 'Save'")
        self.assertEqual(changes[0].detail, f"background-color {_GRAY} -> {_BLUE}")
        self.assertEqual((unexplained_shape, unexplained_color), ([], []))

    def test_text_change_explained(self):
        changes, _, _ = explain_paint([BUTTON], [], _button_page("Save", {}), _button_page("Submit", {}))

        self.assertEqual(changes[0].kind, Kind.SHAPE)
        self.assertEqual(changes[0].detail, "text 'Save' -> 'Submit'")

    def test_color_and_font_change_is_color_and_shape(self):
        before = _button_page("Save", {"background-color": _GRAY, "font-size": "16px"})
        after = _button_page("Save", {"background-color": _BLUE, "font-size": "20px"})
        changes, _, _ = explain_paint([BUTTON], [], before, after)

        self.assertEqual(changes[0].kind, Kind.COLOR_AND_SHAPE)
        self.assertEqual(changes[0].detail, f"background-color {_GRAY} -> {_BLUE}; font-size 16px -> 20px")

    def test_border_color_following_color_left_out(self):
        before = _button_page("Save", {"color": _BLACK, "border-top-color": _BLACK})
        after = _button_page("Save", {"color": _WHITE, "border-top-color": _WHITE})
        changes, _, _ = explain_paint([], [BUTTON], before, after)

        self.assertEqual(changes[0].detail, f"color {_BLACK} -> {_WHITE}")

    def test_layout_styles_left_out(self):
        before = _button_page("Save", {"width": "128px", "padding-top": "8px"})
        after = _button_page("Save", {"width": "160px", "padding-top": "12px"})
        changes, unexplained_shape, _ = explain_paint([BUTTON], [], before, after)

        self.assertEqual(changes, [])
        self.assertEqual(unexplained_shape, [BUTTON])

    def test_boxes_on_one_element_merge_into_one_change(self):
        before = _button_page("Save", {"border-top-color": _GRAY})
        after = _button_page("Save", {"border-top-color": _BLUE})

        top_edge, bottom_edge = Box(120, 96, 248, 99), Box(120, 133, 248, 136)
        changes, _, _ = explain_paint([], [top_edge, bottom_edge], before, after)

        self.assertEqual([change.after for change in changes], [BUTTON])

    def test_inherited_color_reported_on_parent(self):
        paragraph = Box(24, 96, 480, 120)

        def page(color: str) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=PAGE),
                element(1, 0, "section", box=Box(0, 64, 960, 320), styles={"color": color}),
                element(2, 1, "p", "We deliver food.", box=paragraph, styles={"color": color}),
            )

        changes, _, _ = explain_paint([], [paragraph], page(_BLACK), page(_BLUE))
        self.assertEqual([change.element for change in changes], ["<section> containing 'We deliver food.'"])

    def test_equal_boxes_pick_the_one_painted_on_top(self):
        def page(background: str) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=PAGE),
                element(1, 0, "div", "Are you sure?", box=PAGE, styles={"background-color": background}, paint_order=3),
                element(2, 0, "div", box=PAGE, styles={"background-color": _BLACK}, paint_order=2),
            )

        changes, _, _ = explain_paint([], [PAGE], page(_WHITE), page(_GRAY))
        self.assertEqual([change.element for change in changes], ["<div> 'Are you sure?'"])

    def test_unexplained_box_kept_unless_thin(self):
        unchanged = _button_page("Save", {})
        wide, thin = Box(16, 400, 320, 440), Box(16, 480, 320, 482)
        changes, unexplained_shape, _ = explain_paint([wide, thin], [], unchanged, unchanged)

        self.assertEqual(changes, [])
        self.assertEqual(unexplained_shape, [wide])


if __name__ == "__main__":
    unittest.main()
