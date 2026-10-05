from typing import NamedTuple

from image_diff.dom.diff import PageDiff, changed
from image_diff.dom.match import ElementPair
from image_diff.model import OVERLAP_TOLERANCE_PX, SIZE_TOLERANCE_PX, Box, Edge, Element, overlapping

# Container styles that place its children
_PLACEMENT_STYLES = [
    "display", "flex-*", "grid-*", "column-*", "justify-*", "align-*", "*gap", "text-align", "direction", "writing-mode",
]  # fmt: skip


def _outward(box: Box, side: Edge, to: int) -> int:
    if side in (Edge.TOP, Edge.LEFT):
        return box.edge(side) - to
    # Positive when the coordinate lies outside the box on that side
    return to - box.edge(side)


def _beyond(box: Box, side: Edge, other: Box) -> bool:
    # The other box lies past this side of the box
    return _outward(box, side, other.edge(side.opposite)) >= -OVERLAP_TOLERANCE_PX


def relation(box: Box, other: Box) -> Edge | None:
    for side in Edge:
        if side.vertical:
            aligned = overlapping(box.x1, box.x2, other.x1, other.x2)
        else:
            aligned = overlapping(box.y1, box.y2, other.y1, other.y2)
        if aligned and _beyond(box, side.opposite, other):
            return side
    return None


def swapped_sides(pair: ElementPair, other: ElementPair) -> tuple[Edge, Edge] | None:
    was, now = relation(pair.before.box, other.before.box), relation(pair.after.box, other.after.box)
    if was is not None and now is not None and was != now:
        return was, now
    return None


class Claim(NamedTuple):
    pair: ElementPair
    styles: list[str]
    label: str

    @property
    def is_margin(self) -> bool:
        return self.styles[0].startswith("margin-")


class Gap(NamedTuple):
    # Claims in order of preference
    claims: tuple[Claim, ...]
    fallback: Claim
    container: ElementPair
    was: int
    now: int
    before_box: Box
    after_box: Box


def owner(gap: Gap) -> Claim | None:
    for claim in gap.claims:
        if changed(claim.pair, *claim.styles):
            return claim
    return None


def _space_outward(box: Box, side: Edge, to: int, across: Box) -> tuple[int, Box]:
    edge = box.edge(side)
    # Order the corners since the coordinate might lie inside the box
    if side.vertical:
        return _outward(box, side, to), Box(across.x1, min(edge, to), across.x2, max(edge, to))
    return _outward(box, side, to), Box(min(edge, to), across.y1, max(edge, to), across.y2)


def _offsets(side: Edge) -> list[str]:
    # Relative positioning offsets along the side's axis
    return ["top", "bottom"] if side.vertical else ["left", "right"]


def _neighbors(elements: list[Element]) -> list[tuple[Element, Element, Edge]]:
    neighbors = []
    for element in elements:
        for side in (Edge.BOTTOM, Edge.RIGHT):
            following = [other for other in elements if relation(element.box, other.box) == side.opposite]
            # Pair each element with its nearest sibling below it and right of it
            if following:
                nearest = min(following, key=lambda other: other.box.edge(side.opposite))
                neighbors.append((element, nearest, side))
    return neighbors


def _visible_children(page_diff: PageDiff, parent: ElementPair) -> tuple[list[Element], list[Element]]:
    before = [child for child in page_diff.before.children_of(parent.before) if child.visible]
    after = [child for child in page_diff.after.children_of(parent.after) if child.visible]
    return before, after


def _between_siblings(page_diff: PageDiff, parent: ElementPair) -> list[Gap]:
    before_children, after_children = _visible_children(page_diff, parent)
    after_neighbors = {(first.id, second.id, side) for first, second, side in _neighbors(after_children)}
    gaps = []
    for first, second, side in _neighbors(before_children):
        earlier, later = page_diff.by_before.get(first.id), page_diff.by_before.get(second.id)
        # Only a gap between the same neighbors on both pages can be compared
        if not earlier or not later or (earlier.after.id, later.after.id, side) not in after_neighbors:
            continue
        facing = side.opposite
        claims = (
            Claim(earlier, [f"margin-{side}", *_offsets(side)], f"gap {side.word}"),
            Claim(later, [f"margin-{facing}", *_offsets(side)], f"gap {facing.word}"),
            Claim(parent, _PLACEMENT_STYLES, "gap between children"),
        )
        was, before_box = _space_outward(
            earlier.before.box, side, later.before.box.edge(facing), earlier.before.box.union(later.before.box)
        )
        now, after_box = _space_outward(
            earlier.after.box, side, later.after.box.edge(facing), earlier.after.box.union(later.after.box)
        )
        gaps.append(Gap(claims, claims[0], parent, was, now, before_box, after_box))
    return gaps


def _open_sides(element: Element, siblings: list[Element]) -> set[Edge]:
    others = [sibling.box for sibling in siblings if sibling.id != element.id]
    open_sides = set()
    for side in Edge:
        # A side with no sibling past it faces the parent's edge directly
        if not any(_beyond(element.box, side, other) for other in others):
            open_sides.add(side)
    return open_sides


def _to_parent_edges(page_diff: PageDiff, parent: ElementPair) -> list[Gap]:
    before_children, after_children = _visible_children(page_diff, parent)
    insets = []
    for child in page_diff.matched_children(parent):
        open_sides = _open_sides(child.before, before_children) & _open_sides(child.after, after_children)
        for side in Edge:
            if side not in open_sides:
                continue
            claims = (
                Claim(parent, [f"padding-{side}", f"border-{side}-width", *_PLACEMENT_STYLES], f"inner gap at {side}"),
                Claim(child, [f"margin-{side}", *_offsets(side)], f"gap {side.word}"),
            )
            was, before_box = _space_outward(child.before.box, side, parent.before.box.edge(side), child.before.box)
            now, after_box = _space_outward(child.after.box, side, parent.after.box.edge(side), child.after.box)
            insets.append(Gap(claims, claims[1], parent, was, now, before_box, after_box))
    return insets


def changed_gaps(page_diff: PageDiff) -> list[Gap]:
    gaps = []
    for parent in page_diff.matching.pairs:
        if not (parent.before.visible and parent.after.visible):
            continue
        for gap in (*_between_siblings(page_diff, parent), *_to_parent_edges(page_diff, parent)):
            if abs(gap.now - gap.was) > SIZE_TOLERANCE_PX:
                gaps.append(gap)
    return gaps
