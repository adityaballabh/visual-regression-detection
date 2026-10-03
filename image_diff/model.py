from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum

_MAX_LABEL_TEXT = 40


class Side(StrEnum):
    BEFORE = "before"
    AFTER = "after"


class Kind(StrEnum):
    COLOR = "color"
    SHAPE = "shape"


@dataclass(frozen=True)
class Box:
    # Top left and bottom right corners, bottom right is one past the last pixel
    x1: int
    y1: int
    x2: int
    y2: int

    def is_near(self, other: "Box", distance: int) -> bool:
        # Negative when the boxes overlap on that axis
        horizontal_gap = max(self.x1 - other.x2, other.x1 - self.x2)
        vertical_gap = max(self.y1 - other.y2, other.y1 - self.y2)
        return horizontal_gap <= distance and vertical_gap <= distance

    def union(self, other: "Box") -> "Box":
        return Box(min(self.x1, other.x1), min(self.y1, other.y1), max(self.x2, other.x2), max(self.y2, other.y2))


@dataclass(frozen=True)
class Change:
    # None on a side where nothing is drawn, such as an added or removed element
    before: Box | None
    after: Box | None
    kind: Kind


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
    styles: Mapping[str, str]

    @property
    def visible(self) -> bool:
        has_area = self.box.x2 > self.box.x1 and self.box.y2 > self.box.y1
        return has_area and self.styles.get("visibility") != "hidden" and self.styles.get("opacity") != "0"


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

    def _first_text_inside(self, element: Element) -> str | None:
        for candidate in self.elements[element.id + 1 :]:
            if not self._is_inside(candidate, element):
                return None
            if candidate.own_text and candidate.visible:
                return candidate.own_text
        return None

    def _is_inside(self, element: Element, container: Element) -> bool:
        parent = element.parent
        while parent is not None:
            if parent == container.id:
                return True
            parent = self.elements[parent].parent
        return False


def _given_name(element: Element) -> str:
    for key in ("id", "aria-label"):
        if value := element.attributes.get(key):
            return f' {key}="{value}"'
    return ""


def _short_quote(text: str) -> str:
    if len(text) > _MAX_LABEL_TEXT:
        text = text[:_MAX_LABEL_TEXT] + "..."
    return f"'{text}'"
