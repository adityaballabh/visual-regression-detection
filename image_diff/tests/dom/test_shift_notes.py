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
        def widened(link_width: int, size: str, paragraph_y: int) -> Snapshot:
            return snapshot(
                element(0, None, "body", box=Box(0, 0, 800, 200)),
                element(1, 0, "a", "Home", box=Box(0, 0, link_width, 40), styles={"font-size": size}),
                element(2, 0, "p", "Welcome", box=Box(0, paragraph_y, 800, paragraph_y + 40)),
            )

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
                layout_causes(widened(50, "16px", 60), widened(70, "20px", 68)),
                [("<a> 'Home'", "font-size 16px -> 20px; width 50px -> 70px")],
            )
        with self.subTest("wrapped row"):
            self.assertEqual(
                layout_causes(wrapped(100, "16px", Box(100, 0, 200, 40)), wrapped(140, "24px", Box(0, 40, 100, 80))),
                [("<a> 'Home'", "font-size 16px -> 24px; width 100px -> 140px. content moved 40px down, 100px left")],
            )

    def test_sideways_swap_only_pushes_sideways(self):
        def page(first: str, second: str, padding: int) -> Snapshot:
            row_height = 40 + 2 * padding
            ship = Box(220, 0, 320 + 2 * padding, row_height)
            return snapshot(
                element(0, None, "body", box=Box(0, 0, 400, row_height + 100)),
                element(1, 0, "nav", box=Box(0, 0, 400, row_height), styles={"display": "flex"}),
                element(2, 1, "div", first, box=Box(0, 0, 100, row_height)),
                element(3, 1, "div", second, box=Box(110, 0, 210, row_height)),
                element(
                    4,
                    1,
                    "div",
                    "Ship",
                    box=ship,
                    styles={"padding-top": f"{padding}px", "padding-left": f"{padding}px"},
                ),
                element(5, 0, "p", "Welcome", box=Box(0, row_height, 400, row_height + 100)),
            )

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
