import unittest

from image_diff.model import Box, Snapshot
from image_diff.tests.fixtures import FLEX, Block, element, layout_causes, row, snapshot, stack


class ShiftNotesTests(unittest.TestCase):
    def test_pushed_cause_notes_only_its_own_shift(self):
        def stacked(heading_height: int, section_height: int, heading_size: str, section_size: str) -> Snapshot:
            heading = Block("h1", "Menu", heading_height, {"font-size": heading_size})
            section = Block("section", "Contact", section_height, {"font-size": section_size})
            return stack(heading, section, Block("footer", "Footer", 100))

        def side_by_side(width: int, size: str) -> Snapshot:
            font = {"font-size": size}
            links = (
                Block("a", "Home", width, font),
                Block("a", "About", width, font, margin=10),
                Block("a", "Blog", 50, margin=10),
            )
            return row(*links, width=600, styles=FLEX)

        with self.subTest("stacked"):
            self.assertEqual(
                layout_causes(stacked(24, 40, "24px", "16px"), stacked(32, 50, "32px", "20px")),
                [
                    ("<h1> 'Menu'", "font-size 24px -> 32px; height 24px -> 32px. content moved 8px down"),
                    ("<section> 'Contact'", "font-size 16px -> 20px; height 40px -> 50px. content moved 10px down"),
                ],
            )
        with self.subTest("side by side"):
            self.assertEqual(
                layout_causes(side_by_side(50, "16px"), side_by_side(70, "20px")),
                [
                    ("<a> 'Home'", "font-size 16px -> 20px; width 50px -> 70px. content moved 20px right"),
                    ("<a> 'About'", "font-size 16px -> 20px; width 50px -> 70px. content moved 20px right"),
                ],
            )

    def test_resize_pushes_along_its_axis(self):
        def widened(link_width: int, size: str, paragraph_margin: int) -> Snapshot:
            link = Block("a", "Home", 40, {"font-size": size}, across=link_width)
            return stack(link, Block("p", "Welcome", 40, margin=paragraph_margin), width=800, height=200)

        def wrapped(link_width: int, size: str, about: Box) -> Snapshot:
            nav_height = about.y2
            return snapshot(
                element(0, None, "body", box=Box(0, 0, 200, nav_height + 100)),
                element(1, 0, "nav", box=Box(0, 0, 200, nav_height), styles={"display": "flex", "flex-wrap": "wrap"}),
                element(2, 1, "a", "Home", box=Box(0, 0, link_width, 40), styles={"font-size": size}),
                element(3, 1, "a", "About", box=about),
                element(4, 0, "p", "Welcome", box=Box(0, nav_height, 200, nav_height + 100)),
            )

        with self.subTest("widened link"):
            self.assertEqual(
                layout_causes(widened(50, "16px", 20), widened(70, "20px", 28)),
                [("<a> 'Home'", "font-size 16px -> 20px; width 50px -> 70px")],
            )
        with self.subTest("wrapped row"):
            self.assertEqual(
                layout_causes(wrapped(100, "16px", Box(100, 0, 200, 40)), wrapped(140, "24px", Box(0, 40, 100, 80))),
                [("<a> 'Home'", "font-size 16px -> 24px; width 100px -> 140px. content moved 40px down, 100px left")],
            )

    def test_sideways_swap_only_pushes_sideways(self):
        def page(first: str, second: str, padding: int) -> Snapshot:
            ship_styles = {"padding-top": f"{padding}px", "padding-left": f"{padding}px"}
            cards = (
                Block("div", first, 100),
                Block("div", second, 100, margin=10),
                Block("div", "Ship", 100 + 2 * padding, ship_styles, margin=10),
            )
            nav = Block("nav", size=40 + 2 * padding, styles=FLEX, children=cards, children_in_row=True)
            return stack(nav, Block("p", "Welcome", 100), width=400)

        self.assertEqual(
            layout_causes(page("Design", "Build", 0), page("Build", "Design", 12)),
            [
                (
                    "<div> 'Build'",
                    "moved from right of <div> 'Design' to left of <div> 'Design'. content moved 110px right",
                ),
                (
                    "<div> 'Ship'",
                    (
                        "padding-left 0px -> 12px; padding-top 0px -> 12px; width 100px -> 124px; height 40px -> 64px. "
                        "content moved 24px down"
                    ),
                ),
            ],
        )

    def test_transform_pushes_nothing(self):
        def page(button_margin: int, transform: str, paragraph_margin: int, intro: bool) -> Snapshot:
            blocks = [Block("h1", "Intro", 50)] if intro else []
            button = Block(
                "button", "Get Started", 40, {"transform": transform}, margin=button_margin, offset=24, across=120
            )
            blocks += [button, Block("p", "Welcome", 20, margin=paragraph_margin, offset=24, across=240)]
            return stack(*blocks, width=800)

        before = page(0, "none", 10, intro=True)
        after = page(30, "matrix(1, 0, 0, 1, 0, 30)", -20, intro=False)
        self.assertEqual(
            layout_causes(before, after),
            [
                ("<h1> 'Intro'", "removed. content moved 50px up"),
                ("<button> 'Get Started'", "transform none -> matrix(1, 0, 0, 1, 0, 30)"),
            ],
        )

    def test_flex_swap_pushes_only_what_it_crossed(self):
        def cards(first: str, second: str, ship_width: int, ship_margin: int, padding: int) -> Snapshot:
            ship = Block("div", "Ship", ship_width, {"padding-left": f"{padding}px"}, margin=ship_margin)
            cards = (Block("div", first, 100), Block("div", second, 100, margin=10), ship)
            return row(*cards, tag="section", width=400, height=60, styles=FLEX)

        # Ship grows on the left as the row rebalances, so its left edge moves without being crossed
        before = cards("Design", "Build", 100, 10, 0)
        after = cards("Build", "Design", 124, -2, 12)
        self.assertEqual(
            layout_causes(before, after),
            [
                (
                    "<div> 'Build'",
                    "moved from right of <div> 'Design' to left of <div> 'Design'. content moved 110px right",
                ),
                ("<div> 'Ship'", "padding-left 0px -> 12px; width 100px -> 124px"),
            ],
        )

    def test_distributing_container_pushes_from_any_side(self):
        def column(button_height: int, size: str) -> Snapshot:
            styles = {"display": "flex", "flex-direction": "column", "justify-content": "flex-end"}
            paragraph = Block("p", "Welcome", 40, margin=300 - button_height - 40)
            button = Block("button", "Get Started", button_height, {"font-size": size})
            return stack(paragraph, button, tag="aside", width=200, height=300, styles=styles)

        def cards(text_offset: int, text_height: int, size: str) -> Snapshot:
            first = Block(
                "div", size=400, offset=text_offset, across=40, children=(Block("p", "Our first product", 400),)
            )
            text = Block("p", "Our second product", 400, {"font-size": size}, offset=16, across=text_height)
            second = Block("div", size=400, children=(text,))
            styles = {"display": "flex", "align-items": "center"}
            return row(first, second, tag="main", width=800, height=text_height + 32, styles=styles)

        def table(text_offset: int, text_height: int, size: str) -> Snapshot:
            cell = {"display": "table-cell", "vertical-align": "middle"}
            label = Block("span", "Total", 92, margin=8, offset=text_offset, across=20)
            value = Block("span", "42", 92, {"font-size": size}, margin=8, offset=8, across=text_height)
            cells = (
                Block("td", size=400, styles=cell, children=(label,)),
                Block("td", size=400, styles=cell, children=(value,)),
            )
            return row(*cells, tag="tr", width=800, height=text_height + 16, styles={"display": "table-row"})

        with self.subTest("bottom aligned column"):
            self.assertEqual(
                layout_causes(column(40, "16px"), column(80, "24px")),
                [("<button> 'Get Started'", "font-size 16px -> 24px; height 40px -> 80px. content moved 40px up")],
            )
        with self.subTest("centered row"):
            self.assertEqual(
                layout_causes(cards(16, 40, "16px"), cards(32, 72, "28px")),
                [("<p> 'Our second product'", "font-size 16px -> 28px; height 40px -> 72px. content moved 16px down")],
            )
        with self.subTest("middle aligned cells"):
            self.assertEqual(
                layout_causes(table(8, 20, "16px"), table(18, 40, "32px")),
                [("<span> '42'", "font-size 16px -> 32px; height 20px -> 40px. content moved 10px down")],
            )

    def test_pushed_margin_credited_to_both(self):
        def page(heading_height: int, size: str, margin: int) -> Snapshot:
            heading = Block("h1", "Menu", heading_height, {"font-size": size})
            section = Block("section", "Contact", 40, {"margin-top": f"{margin}px"}, margin=margin)
            return stack(heading, section, Block("footer", "Footer", 100))

        self.assertEqual(
            layout_causes(page(24, "24px", 10), page(32, "32px", 210)),
            [
                ("<section> 'Contact'", "gap above 10px -> 210px. content moved 200px down"),
                ("<h1> 'Menu'", "font-size 24px -> 32px; height 24px -> 32px. content moved 8px down"),
            ],
        )

    def test_centered_growth_shifts_both_directions(self):
        def centered(middle_width: int, size: str) -> Snapshot:
            middle = Block("a", "Products", middle_width, {"font-size": size}, margin=50)
            links = (Block("a", "Home", 50), middle, Block("a", "About", 50, margin=50))
            return row(*links, width=600, styles={"display": "flex", "justify-content": "center"})

        self.assertEqual(
            layout_causes(centered(80, "16px"), centered(120, "20px")),
            [("<a> 'Products'", "font-size 16px -> 20px; width 80px -> 120px. content moved 20px right, 20px left")],
        )


if __name__ == "__main__":
    unittest.main()
