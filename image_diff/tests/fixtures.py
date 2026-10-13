from collections import defaultdict
from dataclasses import replace

from image_diff.model import Box, Element, Snapshot

_VISIBLE = {"visibility": "visible", "opacity": "1"}
_BOX = Box(0, 0, 100, 40)


def element(
    id: int,
    parent: int | None,
    tag: str = "div",
    own_text: str = "",
    attributes: dict[str, str] | None = None,
    box: Box = _BOX,
    styles: dict[str, str] | None = None,
) -> Element:
    return Element(id, parent, tag, "", (), attributes or {}, own_text, box, styles or _VISIBLE)


def snapshot(*elements: Element) -> Snapshot:
    # Selectors follow from the tree just like the parser builds them
    children_seen: dict[int | None, int] = defaultdict(int)
    selectors: dict[int, str] = {}
    for item in elements:
        children_seen[item.parent] += 1
        step = f"{item.tag}:nth-child({children_seen[item.parent]})"
        selectors[item.id] = step if item.parent is None else f"{selectors[item.parent]} > {step}"
    return Snapshot(tuple(replace(item, selector=selectors[item.id]) for item in elements))
