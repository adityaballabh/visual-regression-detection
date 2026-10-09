# Adapted from WebSee (Mahajan & Halfond, 2015)

from fnmatch import fnmatchcase
from typing import NamedTuple

from image_diff.dom.match import ElementPair, match
from image_diff.model import Box, Change, Element, Kind, Snapshot

# Chromium reports these as sizes and positions layout worked out, so they might change whenever something nearby resizes
_LEFT_TO_LAYOUT = [
    "width", "height", "margin-*", "padding-*", "top", "right", "bottom", "left", "line-height",
    "grid-template-rows", "grid-template-columns", "transform-origin", "perspective-origin",
]  # fmt: skip
# Ignore unexplained boxes this thin since they probably came from anti-aliasing
_NOISE_PX = 2


class _Difference(NamedTuple):
    name: str
    was: str
    now: str

    def __str__(self) -> str:
        return f"{self.name} {self.was} -> {self.now}"


def _text_difference(pair: ElementPair) -> list[_Difference]:
    before, after = pair
    if before.own_text == after.own_text:
        return []
    return [_Difference("text", f"'{before.own_text}'", f"'{after.own_text}'")]


def _left_to_layout(style: str) -> bool:
    return any(fnmatchcase(style, pattern) for pattern in _LEFT_TO_LAYOUT)


def _is_color(style: str) -> bool:
    return style == "color" or style.endswith("-color") or style in ("fill", "stroke")


def _style_differences(pair: ElementPair) -> list[_Difference]:
    before, after = pair
    color_change = (before.styles.get("color"), after.styles.get("color"))
    differences = []

    for name in sorted(before.styles.keys() & after.styles.keys()):
        was, now = before.styles[name], after.styles[name]
        if was == now or _left_to_layout(name):
            continue
        # Skip color styles that only changed because they copy the text color
        if _is_color(name) and name not in ("color", "background-color") and (was, now) == color_change:
            continue
        differences.append(_Difference(name, was, now))
    return differences


def _encloses(outer: Element, inner: Element) -> bool:
    # With equal boxes the one painted on top is the inner, ties broken by document order
    if outer.box == inner.box:
        return (outer.paint_order, outer.id) < (inner.paint_order, inner.id)
    return outer.box.contains(inner.box)


def _innermost(snapshot: Snapshot, box: Box) -> list[Element]:
    hits = [element for element in snapshot.elements if element.visible and element.box.intersection(box)]
    innermost = []
    # Keep only elements that enclose no other overlapping element, which drops containers
    for element in hits:
        if not any(other is not element and _encloses(element, other) for other in hits):
            innermost.append(element)
    return innermost


def _kind(differences: tuple[_Difference, ...]) -> Kind:
    color = any(_is_color(difference.name) for difference in differences)
    shape = any(not _is_color(difference.name) for difference in differences)
    if color and shape:
        return Kind.COLOR_AND_SHAPE
    return Kind.COLOR if color else Kind.SHAPE


def _clip(element_box: Box, box: Box) -> Box:
    # The part of the element the changed box covers
    return element_box.intersection(box) or element_box


def _add_box(boxes: dict[int, tuple[Box, Box]], origin: ElementPair, box: Box):
    # Grow the origin's change by the part of it this box covers
    origin_before, origin_after = origin
    before_box, after_box = _clip(origin_before.box, box), _clip(origin_after.box, box)

    if origin_after.id in boxes:
        grown_before, grown_after = boxes[origin_after.id]
        before_box, after_box = grown_before.union(before_box), grown_after.union(after_box)
    boxes[origin_after.id] = (before_box, after_box)


class _PageDiff:
    def __init__(self, before: Snapshot, after: Snapshot):
        self.before = before
        self.after = after
        matching = match(before, after)
        self.by_before = {pair.before.id: pair for pair in matching.pairs}
        # Everything in paint is keyed by the after page's element id
        self.by_after = {pair.after.id: pair for pair in matching.pairs}
        self.differences: dict[int, tuple[_Difference, ...]] = {}
        for pair in matching.pairs:
            self.differences[pair.after.id] = (*_text_difference(pair), *_style_differences(pair))

    def changed_pairs_under(self, box: Box) -> list[ElementPair]:
        pairs_under: dict[int, ElementPair] = {}
        # Search both pages since the box might sit where an element was before it shrank or moved
        for snapshot, pair_of in ((self.after, self.by_after), (self.before, self.by_before)):
            for element in _innermost(snapshot, box):
                for node in (element, *snapshot.ancestors_of(element)):
                    if pair := pair_of.get(node.id):
                        pairs_under[pair.after.id] = pair
        return [pair for pair in pairs_under.values() if self.differences[pair.after.id]]

    def inherited_from(self, pair: ElementPair) -> ElementPair:
        differences = set(self.differences[pair.after.id])
        origin = pair
        for ancestor in self.after.ancestors_of(pair.after):
            candidate = self.by_after.get(ancestor.id)
            # If all differences in this pair exist in an ancestor, they were inherited from it
            if candidate and differences <= set(self.differences[candidate.after.id]):
                origin = candidate
        return origin

    def change(self, after_id: int, before_box: Box, after_box: Box) -> Change:
        element = self.by_after[after_id].after
        differences = self.differences[after_id]
        return Change(
            before_box,
            after_box,
            _kind(differences),
            element=self.after.label(element),
            selector=element.selector,
            frames=element.frames,
            detail="; ".join(str(difference) for difference in differences),
        )


def explain_paint(
    shape_boxes: list[Box], color_boxes: list[Box], before: Snapshot, after: Snapshot
) -> tuple[list[Change], list[Box], list[Box]]:
    page_diff = _PageDiff(before, after)
    explained: dict[int, tuple[Box, Box]] = {}
    unexplained_shape: list[Box] = []
    unexplained_color: list[Box] = []

    for boxes, unexplained in ((shape_boxes, unexplained_shape), (color_boxes, unexplained_color)):
        for box in boxes:
            pairs = page_diff.changed_pairs_under(box)
            if not pairs and min(box.width, box.height) > _NOISE_PX:
                unexplained.append(box)
            for pair in pairs:
                _add_box(explained, page_diff.inherited_from(pair), box)

    changes = [page_diff.change(after_id, *boxes) for after_id, boxes in explained.items()]
    return changes, unexplained_shape, unexplained_color
