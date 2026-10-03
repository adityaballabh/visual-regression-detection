import unittest

from image_diff.dom.match import Matching, match
from image_diff.model import Box, Element, Snapshot
from image_diff.tests.fixtures import element, snapshot

_PAGE = Box(0, 0, 960, 720)
_HOME, _ABOUT, _BLOG = Box(16, 24, 72, 44), Box(88, 24, 152, 44), Box(168, 24, 224, 44)


def _nav_page(*links: tuple[str, Box]) -> Snapshot:
    body = element(0, None, "body", box=_PAGE)
    nav = element(1, 0, "nav", box=Box(0, 0, 960, 64))
    anchors = []
    for element_id, (text, box) in enumerate(links, start=2):
        anchors.append(element(element_id, 1, "a", text, {"href": "#"}, box))
    return snapshot(body, nav, *anchors)


def _pairs(matching: Matching) -> list[tuple[int, int]]:
    return [(pair.before.id, pair.after.id) for pair in matching.pairs]


def _paired_texts(matching: Matching) -> set[tuple[str, str]]:
    return {(pair.before.own_text, pair.after.own_text) for pair in matching.pairs if pair.before.own_text}


def _texts(elements: tuple[Element, ...]) -> list[str]:
    return [item.own_text for item in elements]


class MatchTests(unittest.TestCase):
    def test_link_removed(self):
        matching = match(_nav_page(("Home", _HOME), ("About", _ABOUT)), _nav_page(("Home", _HOME)))

        self.assertEqual(_texts(matching.removed), ["About"])
        self.assertEqual(matching.added, ())

    def test_id_rename_paired(self):
        def page(button_id: str) -> Snapshot:
            button = element(1, 0, "button", attributes={"id": button_id}, box=Box(100, 100, 220, 140))
            return snapshot(element(0, None, "body", box=_PAGE), button)

        self.assertEqual(_pairs(match(page("save"), page("submit"))), [(0, 0), (1, 1)])

    def test_inserted_wrapper_added(self):
        heading, paragraph = Box(24, 24, 480, 64), Box(24, 88, 720, 152)
        before = snapshot(
            element(0, None, "body", box=_PAGE),
            element(1, 0, "section", box=Box(0, 0, 960, 320)),
            element(2, 1, "h2", "Our Services", box=heading),
            element(3, 1, "p", "We deliver food.", box=paragraph),
        )
        after = snapshot(
            element(0, None, "body", box=_PAGE),
            element(1, 0, "section", box=Box(0, 0, 960, 320)),
            element(2, 1, "div", box=Box(12, 12, 948, 308)),
            element(3, 2, "h2", "Our Services", box=heading),
            element(4, 2, "p", "We deliver food.", box=paragraph),
        )

        matching = match(before, after)

        self.assertEqual(_pairs(matching), [(0, 0), (1, 1), (2, 3), (3, 4)])
        self.assertEqual([item.id for item in matching.added], [2])

    def test_inserted_sibling_added(self):
        before = _nav_page(("Home", _HOME), ("About", _ABOUT))
        after = _nav_page(("News", _HOME), ("Home", _ABOUT), ("About", _BLOG))

        matching = match(before, after)

        self.assertEqual(_paired_texts(matching), {("Home", "Home"), ("About", "About")})
        self.assertEqual(_texts(matching.added), ["News"])

    def test_content_pushed_down_paired(self):
        before = snapshot(
            element(0, None, "body", box=Box(0, 0, 960, 880)),
            element(1, 0, "header", "Example", box=Box(0, 0, 960, 96)),
            element(2, 0, "main", box=Box(0, 96, 960, 480)),
            element(3, 2, "h1", "Welcome", box=Box(24, 120, 480, 164)),
        )
        after = snapshot(
            element(0, None, "body", box=Box(0, 0, 960, 1240)),
            element(1, 0, "div", "Closed on weekends.", box=Box(0, 0, 960, 360)),
            element(2, 0, "header", "Example", box=Box(0, 360, 960, 456)),
            element(3, 0, "main", box=Box(0, 456, 960, 840)),
            element(4, 3, "h1", "Welcome", box=Box(24, 480, 480, 524)),
        )

        matching = match(before, after)

        self.assertEqual(_pairs(matching), [(0, 0), (1, 2), (2, 3), (3, 4)])
        self.assertEqual(_texts(matching.added), ["Closed on weekends."])

    def test_invisible_elements_ignored(self):
        def page(text: str, styles: dict[str, str]) -> Snapshot:
            span = element(1, 0, "span", text, box=Box(16, 16, 112, 40), styles=styles)
            return snapshot(element(0, None, "body", box=_PAGE), span)

        matching = match(page("Tooltip", {"visibility": "hidden"}), page("Toast", {"opacity": "0"}))

        self.assertEqual(_pairs(matching), [(0, 0)])
        self.assertEqual((matching.removed, matching.added), ((), ()))


if __name__ == "__main__":
    unittest.main()
