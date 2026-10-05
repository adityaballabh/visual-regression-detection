import unittest

from image_diff.model import Snapshot
from image_diff.tests.fixtures import FLEX, Block, layout_causes, row, stack

_INTRO = Block("section", "Intro", 24)
_CONTENT = Block("section", "Content", 50)


def _page(intro: Block = _INTRO, content: Block = _CONTENT) -> Snapshot:
    return stack(Block("header", "Header", 24), intro, content, Block("footer", "Footer", 50))


def _nav(logo_width: int, logo_size: str = "20px") -> Snapshot:
    links = (Block("a", "Home", 50), Block("a", "About", 50, margin=10))
    logo = Block("span", "Logo", logo_width, {"font-size": logo_size})
    return row(logo, Block("div", size=400 - logo_width, children=links), width=400, styles=FLEX)


class LayoutChangesTests(unittest.TestCase):
    def test_resize_only_reports_element(self):
        before = _page(intro=Block("section", "Intro", 24, {"font-size": "16px"}))
        after = _page(intro=Block("section", "Intro", 28, {"font-size": "18px"}))

        self.assertEqual(
            layout_causes(before, after),
            [("<section> 'Intro'", "font-size 16px -> 18px; height 24px -> 28px. content moved 4px down")],
        )

    def test_unexplained_resize_reported(self):
        self.assertEqual(
            layout_causes(_page(), _page(intro=Block("section", "Intro", 54))),
            [("<section> 'Intro'", "height 24px -> 54px. content moved 30px down")],
        )

    def test_squeezed_flex_sibling_skipped(self):
        self.assertEqual(
            layout_causes(_nav(100), _nav(130, logo_size="24px")),
            [("<span> 'Logo'", "font-size 20px -> 24px; width 100px -> 130px. content moved 30px right")],
        )

    def test_inherited_font_size_on_ancestor(self):
        def page(size: str, line_height: int) -> Snapshot:
            font = {"font-size": size}
            lines = (Block("p", "We deliver food.", line_height, font), Block("p", "Order online.", line_height, font))
            return stack(
                Block("section", size=2 * line_height, styles=font, children=lines), Block("footer", "Footer", 100)
            )

        self.assertEqual(
            layout_causes(page("16px", 24), page("20px", 30)),
            [
                (
                    "<section> containing 'We deliver food.'",
                    "font-size 16px -> 20px; height 48px -> 60px. content moved 12px down",
                )
            ],
        )

    def test_widening_text_in_detail(self):
        before, after = row(Block("a", "About", 39), width=400), row(Block("a", "About Us", 60), width=400)

        self.assertEqual(
            layout_causes(before, after), [("<a> 'About Us'", "text 'About' -> 'About Us'; width 39px -> 60px")]
        )

    def test_margin_gap_blamed_on_margin(self):
        before = _page(content=Block("section", "Content", 50, {"margin-top": "0px"}))
        after = _page(content=Block("section", "Content", 50, {"margin-top": "200px"}, margin=200))

        self.assertEqual(
            layout_causes(before, after), [("<section> 'Content'", "gap above 0px -> 200px. content moved 200px down")]
        )

    def test_unexplained_gap_blamed_on_earlier_sibling(self):
        self.assertEqual(
            layout_causes(_page(), _page(content=Block("section", "Content", 50, margin=30))),
            [("<section> 'Intro'", "gap below 0px -> 30px. content moved 30px down")],
        )

    def test_gap_closed_by_grown_sibling_skipped(self):
        def spread(home_width: int, size: str) -> Snapshot:
            links = (Block("a", "Home", home_width, {"font-size": size}), Block("a", "About", 60))
            return row(*links, width=400, styles={"display": "flex", "justify-content": "space-between"})

        self.assertEqual(
            layout_causes(spread(60, "16px"), spread(100, "24px")),
            [("<a> 'Home'", "font-size 16px -> 24px; width 60px -> 100px")],
        )

    def test_auto_margin_following_resize_skipped(self):
        def header(links: int) -> Snapshot:
            anchors = tuple(Block("a", f"Link {index}", 50, margin=10 * min(index, 1)) for index in range(links))
            nav = Block("nav", size=60 * links - 10, styles={"margin-left": f"{350 - 60 * links}px"}, children=anchors)
            return row(
                Block("a", "Brand", 60), nav, width=400, styles={"display": "flex", "justify-content": "space-between"}
            )

        self.assertEqual(layout_causes(header(2), header(3)), [("<a> 'Link 2'", "added. content moved 60px left")])

    def test_padding_inset_blamed_on_parent(self):
        def page(padding: int) -> Snapshot:
            styles = {"padding-top": f"{padding}px"}
            return stack(Block("p", "Welcome"), tag="section", padding=padding, height=padding + 48, styles=styles)

        self.assertEqual(
            layout_causes(page(8), page(24)), [("<section> containing 'Welcome'", "inner gap at top 8px -> 24px")]
        )

    def test_removed_subtree_reported_once(self):
        gone = (Block("p", "Gone", 50), Block("button", "Also gone", 40))
        before = stack(Block("div", size=100, children=gone), Block("footer", "Footer", 100))
        after = stack(Block("footer", "Footer", 100))

        self.assertEqual(layout_causes(before, after), [("<div> containing 'Gone'", "removed. content moved 100px up")])


if __name__ == "__main__":
    unittest.main()
