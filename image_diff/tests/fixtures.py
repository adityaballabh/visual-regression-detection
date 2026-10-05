from __future__ import annotations

from collections import defaultdict
from dataclasses import replace
from typing import NamedTuple

from image_diff.dom.diff import PageDiff
from image_diff.dom.layout_changes import explain_layout
from image_diff.dom.match import match
from image_diff.model import Box, Element, Snapshot

PAGE = Box(0, 0, 960, 720)
FLEX = {"display": "flex"}

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
    paint_order: int = 1,
    text_box: Box | None = None,
) -> Element:
    return Element(id, parent, tag, "", (), attributes or {}, own_text, box, paint_order, styles or _VISIBLE, text_box)


def snapshot(*elements: Element) -> Snapshot:
    # Selectors follow from the tree just like the parser builds them
    children_seen: dict[int | None, int] = defaultdict(int)
    selectors: dict[int, str] = {}
    for item in elements:
        children_seen[item.parent] += 1
        step = f"{item.tag}:nth-child({children_seen[item.parent]})"
        selectors[item.id] = step if item.parent is None else f"{selectors[item.parent]} > {step}"
    return Snapshot(tuple(replace(item, selector=selectors[item.id]) for item in elements))


class Block(NamedTuple):
    tag: str
    text: str = ""
    # Height in a stack, width in a row
    size: int = 40
    styles: dict[str, str] | None = None
    children: tuple[Block, ...] = ()
    margin: int = 0
    padding: int = 0
    attributes: dict[str, str] | None = None


def _place(blocks: tuple[Block, ...], parent: int, start: int, across: Box, vertical: bool, elements: list[Element]):
    position = start
    for block in blocks:
        position += block.margin
        if vertical:
            box = Box(across.x1, position, across.x2, position + block.size)
        else:
            box = Box(position, across.y1, position + block.size, across.y2)
        element_id = len(elements)
        elements.append(element(element_id, parent, block.tag, block.text, block.attributes, box, block.styles))
        _place(block.children, element_id, position + block.padding, box, vertical, elements)
        position += block.size


def _extent(blocks: tuple[Block, ...]) -> int:
    return sum(block.margin + block.size for block in blocks)


def stack(
    *blocks: Block,
    tag: str = "body",
    width: int = 800,
    x: int = 0,
    padding: int = 0,
    height: int | None = None,
    styles: dict[str, str] | None = None,
) -> Snapshot:
    if height is None:
        height = padding + _extent(blocks)
    box = Box(x, 0, x + width, height)
    elements = [element(0, None, tag, box=box, styles=styles)]
    _place(blocks, 0, padding, box, True, elements)
    return snapshot(*elements)


def row(
    *blocks: Block, tag: str = "nav", width: int | None = None, height: int = 40, styles: dict[str, str] | None = None
) -> Snapshot:
    styles = styles or {}
    if width is None:
        width = _extent(blocks)
    box = Box(0, 0, width, height)
    elements = [element(0, None, tag, box=box, styles=styles)]
    justify = styles.get("justify-content")
    if justify == "center":
        _place(blocks, 0, (width - _extent(blocks)) // 2, box, False, elements)
    elif justify == "space-between":
        first, last = blocks[0], blocks[-1]
        _place((first,), 0, 0, box, False, elements)
        _place((last,), 0, width - last.size, box, False, elements)
    else:
        _place(blocks, 0, 0, box, False, elements)
    return snapshot(*elements)


def layout_causes(before: Snapshot, after: Snapshot) -> list[tuple[str, str]]:
    causes, _ = explain_layout(PageDiff(before, after, match(before, after)))
    described = []
    for cause in causes:
        # A removed cause only has a before element to label
        label = after.label(cause.after) if cause.after else before.label(cause.before)
        described.append((label, cause.detail))
    return described
