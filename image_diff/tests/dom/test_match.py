import unittest

from image_diff.dom.match import Matching, match
from image_diff.model import Element, Snapshot
from image_diff.tests.fixtures import Block, row, stack


def _nav(*texts: str) -> Snapshot:
    links = [Block("a", text, 56, margin=16, attributes={"href": "#"}) for text in texts]
    return row(*links, width=960, height=64)


def _pairs(matching: Matching) -> list[tuple[int, int]]:
    return [(pair.before.id, pair.after.id) for pair in matching.pairs]


def _paired_texts(matching: Matching) -> set[tuple[str, str]]:
    return {(pair.before.own_text, pair.after.own_text) for pair in matching.pairs if pair.before.own_text}


def _texts(elements: tuple[Element, ...]) -> list[str]:
    return [item.own_text for item in elements]


class MatchTests(unittest.TestCase):
    def test_link_removed(self):
        matching = match(_nav("Home", "About"), _nav("Home"))

        self.assertEqual(_texts(matching.removed), ["About"])
        self.assertEqual(matching.added, ())

    def test_id_rename_paired(self):
        def page(button_id: str) -> Snapshot:
            return stack(Block("button", size=40, margin=100, attributes={"id": button_id}), x=100, width=120)

        self.assertEqual(_pairs(match(page("save"), page("submit"))), [(0, 0), (1, 1)])

    def test_inserted_wrapper_added(self):
        def content(offset: int) -> tuple[Block, Block]:
            heading = Block("h2", "Our Services", 40, margin=24, offset=offset, across=456)
            return heading, Block("p", "We deliver food.", 64, margin=24, offset=offset, across=696)

        before = stack(Block("section", size=320, children=content(24)), width=960, height=720)
        wrapper = Block("div", size=296, margin=12, offset=12, across=936, children=content(12))
        after = stack(Block("section", size=320, children=(wrapper,)), width=960, height=720)

        matching = match(before, after)

        self.assertEqual(_pairs(matching), [(0, 0), (1, 1), (2, 3), (3, 4)])
        self.assertEqual([item.id for item in matching.added], [2])

    def test_inserted_sibling_added(self):
        before, after = _nav("Home", "About"), _nav("News", "Home", "About")

        matching = match(before, after)

        self.assertEqual(_paired_texts(matching), {("Home", "Home"), ("About", "About")})
        self.assertEqual(_texts(matching.added), ["News"])

    def test_content_pushed_down_paired(self):
        def page(banner: bool) -> Snapshot:
            blocks = [Block("div", "Closed on weekends.", 360)] if banner else []
            heading = Block("h1", "Welcome", 44, offset=24, across=456)
            blocks += [Block("header", "Example", 96), Block("main", size=384, padding=24, children=(heading,))]
            return stack(*blocks, width=960, height=1240 if banner else 880)

        matching = match(page(False), page(True))

        self.assertEqual(_pairs(matching), [(0, 0), (1, 2), (2, 3), (3, 4)])
        self.assertEqual(_texts(matching.added), ["Closed on weekends."])

    def test_invisible_elements_ignored(self):
        def page(text: str, styles: dict[str, str]) -> Snapshot:
            return stack(Block("span", text, 24, styles, margin=16), x=16, width=96)

        matching = match(page("Tooltip", {"visibility": "hidden"}), page("Toast", {"opacity": "0"}))

        self.assertEqual(_pairs(matching), [(0, 0)])
        self.assertEqual((matching.removed, matching.added), ((), ()))


if __name__ == "__main__":
    unittest.main()
