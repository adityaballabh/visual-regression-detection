import unittest

from image_diff.dom.diff import PageDiff
from image_diff.dom.layout_changes import explain_layout
from image_diff.dom.match import match
from image_diff.model import Box, Snapshot
from image_diff.tests.fixtures import element, snapshot


def _causes(before: Snapshot, after: Snapshot) -> list[tuple[str, str]]:
    page_diff = PageDiff(before, after, match(before, after))
    described = []
    for cause in explain_layout(page_diff):
        label = after.label(cause.after) if cause.after else before.label(cause.before)
        described.append((label, cause.detail))
    return described


def _page(intro_height: int = 24, intro_styles: dict[str, str] | None = None) -> Snapshot:
    content_y = 24 + intro_height
    return snapshot(
        element(0, None, "body", box=Box(0, 0, 800, content_y + 100)),
        element(1, 0, "header", "Header", box=Box(0, 0, 800, 24)),
        element(2, 0, "section", "Intro", box=Box(0, 24, 800, 24 + intro_height), styles=intro_styles),
        element(3, 0, "section", "Content", box=Box(0, content_y, 800, content_y + 50)),
        element(4, 0, "footer", "Footer", box=Box(0, content_y + 50, 800, content_y + 100)),
    )


def _nav(logo_width: int, logo_size: str = "20px") -> Snapshot:
    return snapshot(
        element(0, None, "nav", box=Box(0, 0, 400, 40), styles={"display": "flex"}),
        element(1, 0, "span", "Logo", box=Box(0, 0, logo_width, 40), styles={"font-size": logo_size}),
        element(2, 0, "div", box=Box(logo_width, 0, 400, 40)),
        element(3, 2, "a", "Home", box=Box(logo_width, 10, logo_width + 50, 30)),
        element(4, 2, "a", "About", box=Box(logo_width + 60, 10, logo_width + 110, 30)),
    )


class LayoutChangesTests(unittest.TestCase):
    def test_resize_only_reports_element(self):
        before = _page(intro_styles={"font-size": "16px"})
        after = _page(intro_height=28, intro_styles={"font-size": "18px"})

        self.assertEqual(
            _causes(before, after),
            [("<section> 'Intro'", "font-size 16px -> 18px; height 24px -> 28px. content moved 4px down")],
        )

    def test_unexplained_resize_reported(self):
        self.assertEqual(
            _causes(_page(), _page(intro_height=54)),
            [("<section> 'Intro'", "height 24px -> 54px. content moved 30px down")],
        )

    def test_squeezed_flex_sibling_skipped(self):
        self.assertEqual(
            _causes(_nav(100), _nav(130, logo_size="24px")),
            [("<span> 'Logo'", "font-size 20px -> 24px; width 100px -> 130px. content moved 30px right")],
        )

    def test_inherited_font_size_on_ancestor(self):
        def page(size: str, line_height: int) -> Snapshot:
            font = {"font-size": size}
            first_line, second_line = Box(0, 0, 800, line_height), Box(0, line_height, 800, 2 * line_height)
            return snapshot(
                element(0, None, "body", box=Box(0, 0, 800, second_line.y2 + 100)),
                element(1, 0, "section", box=first_line.union(second_line), styles=font),
                element(2, 1, "p", "We deliver food.", box=first_line, styles=font),
                element(3, 1, "p", "Order online.", box=second_line, styles=font),
                element(4, 0, "footer", "Footer", box=Box(0, second_line.y2, 800, second_line.y2 + 100)),
            )

        self.assertEqual(
            _causes(page("16px", 24), page("20px", 30)),
            [
                (
                    "<section> containing 'We deliver food.'",
                    "font-size 16px -> 20px; height 48px -> 60px. content moved 12px down",
                )
            ],
        )

    def test_widening_text_in_detail(self):
        def page(text: str, width: int) -> Snapshot:
            return snapshot(
                element(0, None, "nav", box=Box(0, 0, 400, 40)),
                element(1, 0, "a", text, box=Box(0, 10, width, 30)),
            )

        self.assertEqual(
            _causes(page("About", 39), page("About Us", 60)),
            [("<a> 'About Us'", "text 'About' -> 'About Us'; width 39px -> 60px")],
        )

    def test_stacked_causes_note_their_own_shift(self):
        def page(heading_height: int, section_height: int, heading_size: str, section_size: str) -> Snapshot:
            section_y = heading_height
            footer_y = section_y + section_height
            return snapshot(
                element(0, None, "body", box=Box(0, 0, 800, footer_y + 100)),
                element(1, 0, "h1", "Menu", box=Box(0, 0, 800, heading_height), styles={"font-size": heading_size}),
                element(
                    2, 0, "section", "Home", box=Box(0, section_y, 800, footer_y), styles={"font-size": section_size}
                ),
                element(3, 0, "footer", "Footer", box=Box(0, footer_y, 800, footer_y + 100)),
            )

        self.assertEqual(
            _causes(page(24, 40, "24px", "16px"), page(32, 50, "32px", "20px")),
            [
                ("<h1> 'Menu'", "font-size 24px -> 32px; height 24px -> 32px. content moved 8px down"),
                ("<section> 'Home'", "font-size 16px -> 20px; height 40px -> 50px. content moved 10px down"),
            ],
        )

    def test_removed_subtree_reported_once(self):
        before = snapshot(
            element(0, None, "body", box=Box(0, 0, 800, 200)),
            element(1, 0, "div", box=Box(0, 0, 800, 100)),
            element(2, 1, "p", "Gone", box=Box(0, 0, 800, 50)),
            element(3, 1, "button", "Also gone", box=Box(0, 50, 120, 90)),
            element(4, 0, "footer", "Footer", box=Box(0, 100, 800, 200)),
        )
        after = snapshot(
            element(0, None, "body", box=Box(0, 0, 800, 100)),
            element(1, 0, "footer", "Footer", box=Box(0, 0, 800, 100)),
        )

        self.assertEqual(_causes(before, after), [("<div> containing 'Gone'", "removed. content moved 100px up")])

    def test_invisible_ignored(self):
        def page(height: int) -> Snapshot:
            hidden = element(1, 0, "div", box=Box(0, 0, 800, height), styles={"visibility": "hidden"})
            return snapshot(element(0, None, "body", box=Box(0, 0, 800, 100)), hidden)

        self.assertEqual(_causes(page(40), page(80)), [])

    def test_centered_growth_shifts_both_directions(self):
        def row(middle_width: int, size: str) -> Snapshot:
            half = middle_width // 2
            return snapshot(
                element(0, None, "nav", box=Box(0, 0, 600, 40), styles={"display": "flex"}),
                element(1, 0, "a", "Home", box=Box(200 - half, 10, 250 - half, 30)),
                element(2, 0, "a", "Products", box=Box(300 - half, 10, 300 + half, 30), styles={"font-size": size}),
                element(3, 0, "a", "About", box=Box(350 + half, 10, 400 + half, 30)),
            )

        self.assertEqual(
            _causes(row(80, "16px"), row(120, "20px")),
            [("<a> 'Products'", "font-size 16px -> 20px; width 80px -> 120px. content moved 20px right, 20px left")],
        )


if __name__ == "__main__":
    unittest.main()
