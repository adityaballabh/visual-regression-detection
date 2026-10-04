import unittest

from image_diff.dom.box_changes import explain_boxes
from image_diff.dom.diff import PageDiff
from image_diff.dom.layout_changes import Cause
from image_diff.dom.match import match
from image_diff.model import Box, Change, Kind, Snapshot
from image_diff.tests.fixtures import BUTTON, PAGE, element, snapshot

_GRAY = "rgb(107, 114, 128)"
_BLUE = "rgb(37, 99, 235)"
_BLACK = "rgb(0, 0, 0)"
_WHITE = "rgb(255, 255, 255)"


def _boxes(
    shape_boxes: list[Box], color_boxes: list[Box], before: Snapshot, after: Snapshot
) -> tuple[list[Change], list[Box], list[Box]]:
    return explain_boxes(shape_boxes, color_boxes, PageDiff(before, after, match(before, after)), [])


def _button_page(text: str, styles: dict[str, str]) -> Snapshot:
    return snapshot(
        element(0, None, "body", box=PAGE),
        element(1, 0, "h2", "Settings", box=Box(120, 40, 360, 72)),
        element(2, 0, "button", text, {"class": "btn btn-primary"}, BUTTON, styles),
    )


class BoxChangesTests(unittest.TestCase):
    def test_background_change_explained(self):
        before = _button_page("Save", {"background-color": _GRAY})
        after = _button_page("Save", {"background-color": _BLUE})
        changes, unexplained_shape, unexplained_color = _boxes([], [BUTTON], before, after)

        self.assertEqual(len(changes), 1)
        self.assertEqual(changes[0].kind, Kind.COLOR)
        self.assertEqual(changes[0].element, "<button> 'Save'")
        self.assertEqual(changes[0].detail, f"background-color {_GRAY} -> {_BLUE}")
        self.assertEqual((unexplained_shape, unexplained_color), ([], []))

    def test_text_color_and_font_is_both(self):
        before = _button_page("Save", {"background-color": _GRAY, "font-size": "16px"})
        after = _button_page("Submit", {"background-color": _BLUE, "font-size": "20px"})
        changes, _, _ = _boxes([BUTTON], [], before, after)

        self.assertEqual(changes[0].kind, Kind.COLOR_AND_SHAPE)
        self.assertEqual(
            changes[0].detail, f"text 'Save' -> 'Submit'; background-color {_GRAY} -> {_BLUE}; font-size 16px -> 20px"
        )

    def test_layout_and_copied_colors_skipped(self):
        before = _button_page("Save", {"color": _BLACK, "border-top-color": _BLACK, "width": "128px"})
        after = _button_page("Save", {"color": _WHITE, "border-top-color": _WHITE, "width": "160px"})
        changes, _, _ = _boxes([], [BUTTON], before, after)

        self.assertEqual(changes[0].detail, f"color {_BLACK} -> {_WHITE}")

    def test_boxes_on_one_element_merge(self):
        before = _button_page("Save", {"border-top-color": _GRAY})
        after = _button_page("Save", {"border-top-color": _BLUE})

        top_edge, bottom_edge = Box(120, 96, 248, 99), Box(120, 133, 248, 136)
        changes, _, _ = _boxes([], [top_edge, bottom_edge], before, after)

        self.assertEqual([change.after for change in changes], [BUTTON])

    def test_inherited_color_on_ancestor(self):
        paragraph = Box(24, 96, 480, 120)

        def page(color: str) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=PAGE),
                element(1, 0, "section", box=Box(0, 64, 960, 320), styles={"color": color}),
                element(2, 1, "p", "We deliver food.", box=paragraph, styles={"color": color}),
            )

        changes, _, _ = _boxes([], [paragraph], page(_BLACK), page(_BLUE))
        self.assertEqual([change.element for change in changes], ["<section> containing 'We deliver food.'"])

    def test_equal_boxes_pick_top_boxes(self):
        def page(background: str) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=PAGE),
                element(1, 0, "div", "Are you sure?", box=PAGE, styles={"background-color": background}, paint_order=3),
                element(2, 0, "div", box=PAGE, styles={"background-color": _BLACK}, paint_order=2),
            )

        changes, _, _ = _boxes([], [PAGE], page(_WHITE), page(_GRAY))
        self.assertEqual([change.element for change in changes], ["<div> 'Are you sure?'"])

    def test_cause_box_clipped_to_pixels(self):
        before, after = _button_page("Save", {"padding-top": "8px"}), _button_page("Save", {"padding-top": "16px"})
        cause = Cause(before.elements[2], after.elements[2], Kind.SHAPE, "padding-top 8px -> 16px")
        bottom_half = Box(120, 116, 248, 136)

        changes, _, _ = explain_boxes([bottom_half], [], PageDiff(before, after, match(before, after)), [cause])
        self.assertEqual([(change.before, change.after) for change in changes], [(bottom_half, bottom_half)])

    def test_style_change_joins_layout_change(self):
        before = _button_page("Save", {"background-color": _GRAY, "padding-top": "8px"})
        after = _button_page("Save", {"background-color": _BLUE, "padding-top": "16px"})
        cause = Cause(before.elements[2], after.elements[2], Kind.COLOR_AND_SHAPE, "padding-top 8px -> 16px")

        changes, _, _ = explain_boxes([], [BUTTON], PageDiff(before, after, match(before, after)), [cause])
        self.assertEqual([change.detail for change in changes], ["padding-top 8px -> 16px"])

    def test_shifted_content_dropped(self):
        def page(button_y: int) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=PAGE),
                element(1, 0, "h2", "Settings", box=Box(120, 40, 360, 72)),
                element(2, 0, "button", "Save", box=Box(120, button_y, 248, button_y + 40)),
            )

        before, after = page(96), page(128)
        heading = Cause(before.elements[1], after.elements[1], Kind.SHAPE, "height 32px -> 64px")
        moved_button = Box(120, 96, 248, 168)

        changes, unexplained_shape, _ = explain_boxes(
            [moved_button], [], PageDiff(before, after, match(before, after)), [heading]
        )

        self.assertEqual([change.element for change in changes], ["<h2> 'Settings'"])
        self.assertEqual(unexplained_shape, [])

    def test_unexplained_kept_unless_thin(self):
        unchanged = _button_page("Save", {})
        wide, thin = Box(16, 400, 320, 440), Box(16, 480, 320, 482)
        changes, unexplained_shape, _ = _boxes([wide, thin], [], unchanged, unchanged)

        self.assertEqual(changes, [])
        self.assertEqual(unexplained_shape, [wide])


if __name__ == "__main__":
    unittest.main()
