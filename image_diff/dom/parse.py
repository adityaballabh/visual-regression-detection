import json
from collections import ChainMap, defaultdict
from collections.abc import Mapping
from pathlib import Path

from image_diff.model import Box, Element, Snapshot, px

_ELEMENT_NODE = 1
_TEXT_NODE = 3


def _selectors(nodes: dict, strings: list[str]) -> dict[int, str]:
    children_seen: dict[int, int] = defaultdict(int)
    selectors: dict[int, str] = {}
    for node, node_type in enumerate(nodes["nodeType"]):
        if node_type != _ELEMENT_NODE:
            continue
        parent = nodes["parentIndex"][node]
        children_seen[parent] += 1
        tag = strings[nodes["nodeName"][node]].lower()
        step = f"{tag}:nth-child({children_seen[parent]})"
        selectors[node] = f"{selectors[parent]} > {step}" if parent in selectors else step
    return selectors


def _text(nodes: dict, strings: list[str], node: int) -> str:
    return strings[nodes["nodeValue"][node]].strip()


def _text_nodes(nodes: dict, strings: list[str], laid_out: set[int]) -> dict[int, list[int]]:
    text_nodes: dict[int, list[int]] = defaultdict(list)
    for node, node_type in enumerate(nodes["nodeType"]):
        if node_type == _TEXT_NODE and node in laid_out and _text(nodes, strings, node):
            text_nodes[nodes["parentIndex"][node]].append(node)
    return text_nodes


def _attributes(flat: list[int], strings: list[str]) -> dict[str, str]:
    # Chromium lists attributes as name, value, name, value
    names, values = flat[::2], flat[1::2]
    return {strings[name]: strings[value] for name, value in zip(names, values)}


def _nearest_laid_out(nodes: dict, node: int, element_ids: dict[int, int]) -> int:
    # Skip `display: contents` wrappers since they have no layout
    parent = nodes["parentIndex"][node]
    while parent >= 0 and parent not in element_ids:
        parent = nodes["parentIndex"][parent]
    return parent


def _content_origin(left: float, top: float, styles: Mapping[str, str]) -> tuple[float, float]:
    inner_left = left + px(styles["border-left-width"]) + px(styles["padding-left"])
    inner_top = top + px(styles["border-top-width"]) + px(styles["padding-top"])
    return inner_left, inner_top


class _Document:
    def __init__(self, tables: dict, strings: list[str], origin: tuple[float, float], iframe: Element | None):
        self.nodes, self.layout = tables["nodes"], tables["layout"]
        # Where the document's top left corner sits on the page
        self.origin = origin
        self.layout_rows = {node: row for row, node in enumerate(self.layout["nodeIndex"])}
        content_documents = self.nodes["contentDocumentIndex"]
        self.iframe_documents = dict(zip(content_documents["index"], content_documents["value"]))
        self.selectors = _selectors(self.nodes, strings)
        self.strings = strings
        self.text_nodes = _text_nodes(self.nodes, strings, set(self.layout_rows))
        self.frames = (*iframe.frames, iframe.selector) if iframe else ()
        self.root_parent = iframe.id if iframe else None

    def laid_out_elements(self) -> list[int]:
        node_types = enumerate(self.nodes["nodeType"])
        return [node for node, node_type in node_types if node_type == _ELEMENT_NODE and node in self.layout_rows]

    def own_text(self, node: int) -> str:
        return " ".join(_text(self.nodes, self.strings, text_node) for text_node in self.text_nodes[node])

    def page_bounds(self, node: int) -> tuple[float, float, float, float]:
        x, y, width, height = self.layout["bounds"][self.layout_rows[node]]
        return self.origin[0] + x, self.origin[1] + y, width, height

    def paint_order(self, node: int) -> int:
        return self.layout["paintOrders"][self.layout_rows[node]]


class _Loader:
    def __init__(self, capture: dict):
        self.strings = capture["snapshot"]["strings"]
        self.documents = capture["snapshot"]["documents"]
        self.style_names = capture["styles"]
        self.same_everywhere = capture["same_everywhere"]
        self.scale = capture["device_pixel_ratio"]
        self.elements: list[Element] = []

    def load_document(self, index: int, origin: tuple[float, float] = (0.0, 0.0), iframe: Element | None = None):
        document = _Document(self.documents[index], self.strings, origin, iframe)
        element_ids: dict[int, int] = {}
        for node in document.laid_out_elements():
            parent = _nearest_laid_out(document.nodes, node, element_ids)
            element = self._element(document, node, element_ids.get(parent, document.root_parent))
            element_ids[node] = element.id
            self.elements.append(element)

            if node in document.iframe_documents:
                left, top, _, _ = document.page_bounds(node)
                self.load_document(document.iframe_documents[node], _content_origin(left, top, element.styles), element)

    def _text_box(self, document: _Document, node: int) -> Box | None:
        text_box = None
        for text_node in document.text_nodes[node]:
            box = self._box(*document.page_bounds(text_node))
            text_box = box if text_box is None else text_box.union(box)
        return text_box

    def _element(self, document: _Document, node: int, parent: int | None) -> Element:
        row = document.layout_rows[node]
        return Element(
            id=len(self.elements),
            parent=parent,
            tag=self.strings[document.nodes["nodeName"][node]].lower(),
            selector=document.selectors[node],
            frames=document.frames,
            attributes=_attributes(document.nodes["attributes"][node], self.strings),
            own_text=document.own_text(node),
            box=self._box(*document.page_bounds(node)),
            paint_order=document.paint_order(node),
            styles=self._styles(document.layout["styles"][row]),
            text_box=self._text_box(document, node),
        )

    def _styles(self, values: list[int]) -> ChainMap[str, str]:
        own = {}
        for name, value in zip(self.style_names, values):
            # -1 means Chromium left the style out
            if value >= 0:
                own[name] = self.strings[value]
        # Share one copy of the styles that are the same everywhere
        return ChainMap(own, self.same_everywhere)

    def _box(self, left: float, top: float, width: float, height: float) -> Box:
        # Scale to the screenshot's device pixels
        right, bottom = left + width, top + height
        x1, y1, x2, y2 = (round(edge * self.scale) for edge in (left, top, right, bottom))
        return Box(x1, y1, x2, y2)


def parse_snapshot(capture: dict) -> Snapshot:
    loader = _Loader(capture)
    loader.load_document(0)
    return Snapshot(tuple(loader.elements))


def load_snapshot(path: Path) -> Snapshot:
    return parse_snapshot(json.loads(path.read_text()))
