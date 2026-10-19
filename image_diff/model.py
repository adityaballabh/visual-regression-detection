from __future__ import annotations

from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from enum import StrEnum
from functools import cmp_to_key, reduce
from typing import NamedTuple

_MAX_LABEL_TEXT = 40
# Edges round separately on each page, so a size can drift a pixel with nothing changed
SIZE_TOLERANCE_PX = 1
# Rounding drift on each of the two edges
OVERLAP_TOLERANCE_PX = 2 * SIZE_TOLERANCE_PX


class Side(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class Edge(StrEnum):
    TOP = "top"
    RIGHT = "right"
    BOTTOM = "bottom"
    LEFT = "left"

    @property
    def opposite(self) -> Edge:
        return {Edge.TOP: Edge.BOTTOM, Edge.RIGHT: Edge.LEFT, Edge.BOTTOM: Edge.TOP, Edge.LEFT: Edge.RIGHT}[self]

    @property
    def vertical(self) -> bool:
        return self in (Edge.TOP, Edge.BOTTOM)

    @property
    def word(self) -> str:
        return {Edge.TOP: "above", Edge.BOTTOM: "below"}.get(self, self.value)

    @property
    def relation(self) -> str:
        return self.word if self.vertical else f"{self.word} of"

    @property
    def direction(self) -> str:
        return {Edge.TOP: "up", Edge.BOTTOM: "down"}.get(self, self.value)


class Kind(StrEnum):
    COLOR = "color"
    SHAPE = "shape"
    COLOR_AND_SHAPE = "color_and_shape"


@dataclass(frozen=True)
class Box:
    # Top left and bottom right corners, bottom right is one past the last pixel
    x1: int
    y1: int
    x2: int
    y2: int

    @property
    def width(self) -> int:
        return self.x2 - self.x1

    @property
    def height(self) -> int:
        return self.y2 - self.y1

    @property
    def area(self) -> int:
        return self.width * self.height

    def edge(self, side: Edge) -> int:
        return {Edge.TOP: self.y1, Edge.RIGHT: self.x2, Edge.BOTTOM: self.y2, Edge.LEFT: self.x1}[side]

    # Negative when the boxes overlap on that axis
    def horizontal_gap(self, other: Box) -> int:
        return max(self.x1 - other.x2, other.x1 - self.x2)

    def vertical_gap(self, other: Box) -> int:
        return max(self.y1 - other.y2, other.y1 - self.y2)

    def is_near(self, other: Box, distance: int) -> bool:
        return self.horizontal_gap(other) <= distance and self.vertical_gap(other) <= distance

    def union(self, other: Box) -> Box:
        return Box(min(self.x1, other.x1), min(self.y1, other.y1), max(self.x2, other.x2), max(self.y2, other.y2))

    @staticmethod
    def union_all(boxes: Iterable[Box]) -> Box:
        return reduce(Box.union, boxes)

    def intersection(self, other: Box) -> Box | None:
        box = Box(max(self.x1, other.x1), max(self.y1, other.y1), min(self.x2, other.x2), min(self.y2, other.y2))
        return box if box.width > 0 and box.height > 0 else None

    def contains(self, inner: Box) -> bool:
        return self.intersection(inner) == inner


@dataclass(frozen=True)
class Change:
    # None on a side where nothing is drawn, such as an added or removed element
    before: Box | None
    after: Box | None
    kind: Kind
    # Which element changed and how, left as None when the DOM does not explain the change
    element: str | None = None
    selector: str | None = None
    frames: tuple[str, ...] | None = None
    detail: str | None = None


@dataclass(frozen=True)
class Element:
    id: int
    parent: int | None
    tag: str
    selector: str
    # Selectors of the enclosing iframes, outermost first
    frames: tuple[str, ...]
    attributes: dict[str, str]
    own_text: str
    box: Box
    # Chromium stacking layer, higher paints on top
    paint_order: int
    styles: Mapping[str, str]
    # The box around the element's own text
    text_box: Box | None = None

    @property
    def visible(self) -> bool:
        return self.box.area > 0 and self.styles.get("visibility") != "hidden" and self.styles.get("opacity") != "0"


@dataclass(frozen=True)
class Snapshot:
    # In document order so an element's descendants are right after it
    elements: tuple[Element, ...]

    def label(self, element: Element) -> str:
        tag = f"<{element.tag}{_given_name(element)}>"
        if element.own_text:
            return f"{tag} {_short_quote(element.own_text)}"
        if inner_text := self._first_text_inside(element):
            return f"{tag} containing {_short_quote(inner_text)}"
        if image := element.attributes.get("alt") or element.attributes.get("src", "").rsplit("/", 1)[-1]:
            return f"{tag} {_short_quote(image)}"
        return tag

    def children_of(self, element: Element) -> list[Element]:
        return [child for child in self.elements if child.parent == element.id]

    def child_containing(self, container: Element, element: Element) -> Element | None:
        for candidate in (element, *self.ancestors_of(element)):
            if candidate.parent == container.id:
                return candidate
        return None

    def ancestors_of(self, element: Element) -> list[Element]:
        ancestors = []
        parent = element.parent
        while parent is not None:
            ancestors.append(self.elements[parent])
            parent = self.elements[parent].parent
        return ancestors

    def _first_text_inside(self, element: Element) -> str | None:
        for candidate in self.elements[element.id + 1 :]:
            if not self.is_inside(candidate, {element.id}):
                return None
            if candidate.own_text and candidate.visible:
                return candidate.own_text
        return None

    def is_inside(self, element: Element, container_ids: set[int]) -> bool:
        return any(ancestor.id in container_ids for ancestor in self.ancestors_of(element))


def overlapping(start: int, end: int, other_start: int, other_end: int) -> bool:
    return min(end, other_end) - max(start, other_start) > OVERLAP_TOLERANCE_PX


def reading_order(box: Box, other: Box) -> int:
    # Same row left to right, otherwise top to bottom
    if overlapping(box.y1, box.y2, other.y1, other.y2):
        return box.x1 - other.x1
    return box.y1 - other.y1


def in_reading_order[T](items: Iterable[T], box_of: Callable[[T], Box]) -> list[T]:
    return sorted(items, key=cmp_to_key(lambda a, b: reading_order(box_of(a), box_of(b))))


def px(value: str) -> float:
    return float(value.removesuffix("px"))


def _given_name(element: Element) -> str:
    for key in ("id", "aria-label"):
        if value := element.attributes.get(key):
            return f' {key}="{value}"'
    return ""


def _short_quote(text: str) -> str:
    if len(text) > _MAX_LABEL_TEXT:
        text = text[:_MAX_LABEL_TEXT] + "..."
    return f"'{text}'"


class Cause(NamedTuple):
    before: Element | None
    after: Element | None
    kind: Kind
    detail: str
    # The area to report when it is not the element itself, such as a gap
    boxes: tuple[Box, Box] | None = None
    # A reorder, reparent or text move put the element where it is
    moved_itself: bool = False

    @property
    def page_boxes(self) -> tuple[Box | None, Box | None]:
        if self.boxes:
            return self.boxes
        return self.before and self.before.box, self.after and self.after.box
