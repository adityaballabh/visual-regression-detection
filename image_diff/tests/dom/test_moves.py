import unittest

from image_diff.model import Box, Snapshot
from image_diff.tests.fixtures import Block, element, layout_causes, row, snapshot, stack


class MovesTests(unittest.TestCase):
    def test_swap_reported_as_one_reorder(self):
        def nav(first: str, second: str) -> Snapshot:
            return row(Block("a", first, 50), Block("a", second, 50, margin=10), width=400)

        self.assertEqual(
            layout_causes(nav("Home", "About"), nav("About", "Home")),
            [("<a> 'About'", "moved from right of <a> 'Home' to left of <a> 'Home'. content moved 60px right")],
        )

    def test_reparent_names_both_parents(self):
        def page(in_header: bool) -> Snapshot:
            button = (Block("button", "Sign up", 30),)
            header = Block("header", "Header", 50, children=button if in_header else ())
            footer = Block("footer", "Footer", 50, margin=150, children=() if in_header else button)
            return stack(header, footer)

        self.assertEqual(
            layout_causes(page(True), page(False)),
            [("<button> 'Sign up'", "moved from inside <header> 'Header' to inside <footer> 'Footer'")],
        )

    def test_text_align_once_on_container(self):
        def page(align: str, text_x: int) -> Snapshot:
            styles = {"text-align": align}
            text_box = Box(text_x, 5, text_x + 120, 35)
            return snapshot(
                element(0, None, "section", box=Box(0, 0, 800, 100), styles=styles),
                element(1, 0, "h1", "Welcome", box=Box(0, 0, 800, 40), styles=styles, text_box=text_box),
            )

        self.assertEqual(
            layout_causes(page("start", 0), page("center", 340)),
            [("<section> containing 'Welcome'", "text-align start -> center")],
        )

    def test_input_text_align_without_text_box(self):
        def form(align: str) -> Snapshot:
            return stack(Block("input", size=30, styles={"text-align": align}), tag="form", padding=30, height=100)

        self.assertEqual(layout_causes(form("left"), form("right")), [("<input>", "text-align left -> right")])


if __name__ == "__main__":
    unittest.main()
