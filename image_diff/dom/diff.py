from collections.abc import Sequence
from fnmatch import fnmatchcase
from typing import NamedTuple

from image_diff.dom.match import ElementPair, Matching
from image_diff.model import SIZE_TOLERANCE_PX, Kind, Snapshot

# Chromium reports these as sizes and positions layout worked out, so they might change whenever something nearby resizes
_LEFT_TO_LAYOUT = [
    "width", "height", "margin-*", "padding-*", "top", "right", "bottom", "left", "line-height",
    "grid-template-rows", "grid-template-columns", "transform-origin", "perspective-origin",
]  # fmt: skip


class Difference(NamedTuple):
    name: str
    was: str
    now: str

    def __str__(self) -> str:
        return f"{self.name} {self.was} -> {self.now}"


def _text_difference(pair: ElementPair) -> list[Difference]:
    before, after = pair
    if before.own_text == after.own_text:
        return []
    return [Difference("text", f"'{before.own_text}'", f"'{after.own_text}'")]


def matches_any(style: str, patterns: Sequence[str]) -> bool:
    return any(fnmatchcase(style, pattern) for pattern in patterns)


def is_color(style: str) -> bool:
    return style == "color" or style.endswith("-color") or style in ("fill", "stroke")


def changed_styles(pair: ElementPair) -> list[Difference]:
    before, after = pair
    differences = []
    for name in sorted(before.styles.keys() & after.styles.keys()):
        if before.styles[name] != after.styles[name]:
            differences.append(Difference(name, before.styles[name], after.styles[name]))
    return differences


def size_changes(pair: ElementPair) -> list[Difference]:
    changes = []
    for name in ("width", "height"):
        was, now = getattr(pair.before.box, name), getattr(pair.after.box, name)
        if abs(now - was) > SIZE_TOLERANCE_PX:
            changes.append(Difference(name, f"{was}px", f"{now}px"))
    return changes


def resized(pair: ElementPair) -> bool:
    return bool(size_changes(pair))


def same_change(pair: ElementPair, other: ElementPair, style: str) -> bool:
    # Inheritance changes a style from and to the same values on both elements
    return (pair.before.styles.get(style), pair.after.styles.get(style)) == (
        other.before.styles.get(style),
        other.after.styles.get(style),
    )


def changed(pair: ElementPair, *patterns: str) -> bool:
    return any(matches_any(difference.name, patterns) for difference in changed_styles(pair))


def _style_differences(pair: ElementPair) -> list[Difference]:
    before, after = pair
    color_change = (before.styles.get("color"), after.styles.get("color"))
    differences = []
    for difference in changed_styles(pair):
        name, was, now = difference
        if matches_any(name, _LEFT_TO_LAYOUT):
            continue
        # Skip color styles that only changed because they copy the text color
        if is_color(name) and name not in ("color", "background-color") and (was, now) == color_change:
            continue
        differences.append(difference)
    return differences


class PageDiff:
    def __init__(self, before: Snapshot, after: Snapshot, matching: Matching):
        self.before = before
        self.after = after
        self.matching = matching
        self.by_before = {pair.before.id: pair for pair in matching.pairs}
        # Key everything by the after page's element id
        self.by_after = {pair.after.id: pair for pair in matching.pairs}
        self.differences: dict[int, tuple[Difference, ...]] = {}
        for pair in matching.pairs:
            self.differences[pair.after.id] = (*_text_difference(pair), *_style_differences(pair))

    def parent_pair(self, pair: ElementPair) -> ElementPair | None:
        parent = self.by_after.get(pair.after.parent)
        # Only count the parents as a pair when they are matched to each other
        if parent and parent.before.id == pair.before.parent:
            return parent
        return None

    def matched_children(self, parent: ElementPair) -> list[ElementPair]:
        children = []
        for child in self.before.children_of(parent.before):
            pair = self.by_before.get(child.id)
            # Only children that stayed under this parent
            if pair and pair.after.parent == parent.after.id:
                children.append(pair)
        return children

    def own_differences(self, pair: ElementPair) -> list[Difference]:
        inherited = set()
        if parent := self.parent_pair(pair):
            inherited = set(self.differences[parent.after.id])
        own = []
        for difference in self.differences[pair.after.id]:
            # Skip differences the parent shows too since they were inherited from it
            if difference not in inherited:
                own.append(difference)
        return own

    def inherited_from(self, pair: ElementPair, styles: tuple[str, ...] | None = None) -> ElementPair:
        differences = {d for d in self.differences[pair.after.id] if styles is None or d.name in styles}
        # With nothing to match every ancestor would qualify
        if not differences:
            return pair
        origin = pair
        for ancestor in self.after.ancestors_of(pair.after):
            candidate = self.by_after.get(ancestor.id)
            # If all differences in this pair exist in an ancestor, they were inherited from it
            if candidate and differences <= set(self.differences[candidate.after.id]):
                origin = candidate
        return origin


def change_kind(differences: list[Difference]) -> Kind:
    color = any(is_color(difference.name) for difference in differences)
    shape = any(not is_color(difference.name) for difference in differences)
    if color and shape:
        return Kind.COLOR_AND_SHAPE
    return Kind.COLOR if color else Kind.SHAPE
