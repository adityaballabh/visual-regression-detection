# Adapted from WebSee (Mahajan & Halfond, 2015)

from image_diff.dom.diff import PageDiff, change_kind
from image_diff.dom.match import ElementPair
from image_diff.model import Box, Cause, Change, Element, Kind, Snapshot

# Ignore unexplained boxes this thin since they probably came from anti-aliasing
_NOISE_PX = 2

# The reported area on each page, None on a page where the element does not exist
_PageBoxes = tuple[Box | None, Box | None]


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


def _clip(element_box: Box | None, box: Box) -> Box | None:
    if element_box is None:
        return None
    # The part of the element the changed box covers
    return element_box.intersection(box) or element_box


def _union(grown: Box | None, box: Box | None) -> Box | None:
    if grown is None or box is None:
        return grown or box
    return grown.union(box)


def _add_box(boxes: dict[int, _PageBoxes], key: int, before_box: Box | None, after_box: Box | None):
    # Grow the entry's change by these boxes
    if key in boxes:
        grown_before, grown_after = boxes[key]
        before_box, after_box = _union(grown_before, before_box), _union(grown_after, after_box)
    boxes[key] = (before_box, after_box)


def _changed_pairs_under(page_diff: PageDiff, box: Box) -> list[ElementPair]:
    pairs_under: dict[int, ElementPair] = {}
    # Search both pages since the box might sit where an element was before it shrank or moved
    for snapshot, pair_of in ((page_diff.after, page_diff.by_after), (page_diff.before, page_diff.by_before)):
        for element in _innermost(snapshot, box):
            for node in (element, *snapshot.ancestors_of(element)):
                if pair := pair_of.get(node.id):
                    pairs_under[pair.after.id] = pair
    return [pair for pair in pairs_under.values() if page_diff.differences[pair.after.id]]


def _shifted_only(page_diff: PageDiff, box: Box, shifted_ids: set[int]) -> bool:
    shifted = False
    for snapshot, pair_of in ((page_diff.after, page_diff.by_after), (page_diff.before, page_diff.by_before)):
        for element in _innermost(snapshot, box):
            pair = pair_of.get(element.id)
            if pair is None:
                return False
            # Only a move layout credited to a cause counts as shifted content
            shifted = shifted or pair.before.id in shifted_ids
    return shifted


class _Causes:
    def __init__(self, page_diff: PageDiff, causes: list[Cause]):
        self.page_diff = page_diff
        # Index the causes by element id on each page
        self.by_before = {cause.before.id: index for index, cause in enumerate(causes) if cause.before}
        self.by_after = {cause.after.id: index for index, cause in enumerate(causes) if cause.after}

    def under(self, box: Box) -> set[int]:
        found = set()
        for snapshot, index_of in ((self.page_diff.after, self.by_after), (self.page_diff.before, self.by_before)):
            for element in _innermost(snapshot, box):
                for node in (element, *snapshot.ancestors_of(element)):
                    # Stop at the nearest cause above the element
                    if node.id in index_of:
                        found.add(index_of[node.id])
                        break
        return found


def _change(snapshot: Snapshot, element: Element, boxes: _PageBoxes, kind: Kind, detail: str) -> Change:
    before_box, after_box = boxes
    return Change(
        before_box,
        after_box,
        kind,
        element=snapshot.label(element),
        selector=element.selector,
        frames=element.frames,
        detail=detail,
    )


def _paint_change(page_diff: PageDiff, after_id: int, boxes: _PageBoxes) -> Change:
    differences = page_diff.differences[after_id]
    detail = "; ".join(str(difference) for difference in differences)
    return _change(page_diff.after, page_diff.by_after[after_id].after, boxes, change_kind(list(differences)), detail)


def _cause_change(page_diff: PageDiff, cause: Cause, boxes: _PageBoxes) -> Change:
    snapshot, element = (page_diff.after, cause.after) if cause.after else (page_diff.before, cause.before)
    return _change(snapshot, element, boxes, cause.kind, cause.detail)


def explain_boxes(
    shape_boxes: list[Box],
    color_boxes: list[Box],
    page_diff: PageDiff,
    layout_causes: list[Cause],
    shifted_ids: set[int],
) -> tuple[list[Change], list[Box], list[Box]]:
    causes = _Causes(page_diff, layout_causes)
    explained: dict[int, _PageBoxes] = {}
    cause_boxes: dict[int, _PageBoxes] = {}
    unexplained_shape: list[Box] = []
    unexplained_color: list[Box] = []

    for boxes, unexplained in ((shape_boxes, unexplained_shape), (color_boxes, unexplained_color)):
        for box in boxes:
            causes_under = causes.under(box)
            pairs = _changed_pairs_under(page_diff, box)
            for pair in pairs:
                origin = page_diff.inherited_from(pair)
                # Send a style change on a cause's element to the cause instead of its own entry
                if origin.after.id in causes.by_after:
                    causes_under.add(causes.by_after[origin.after.id])
                else:
                    before_box, after_box = _clip(origin.before.box, box), _clip(origin.after.box, box)
                    _add_box(explained, origin.after.id, before_box, after_box)

            for index in causes_under:
                own_before, own_after = layout_causes[index].page_boxes
                if layout_causes[index].boxes is None:
                    _add_box(cause_boxes, index, _clip(own_before, box), _clip(own_after, box))
                else:
                    # A cause with its own box keeps it and grows by the pixels that land on it
                    _add_box(cause_boxes, index, own_before.union(box), own_after.union(box))

            if pairs or causes_under or _shifted_only(page_diff, box, shifted_ids):
                continue
            if min(box.width, box.height) > _NOISE_PX:
                unexplained.append(box)

    changes = [_paint_change(page_diff, after_id, boxes) for after_id, boxes in explained.items()]
    for index, cause in enumerate(layout_causes):
        # Fall back to the whole element when no box landed on the cause
        changes.append(_cause_change(page_diff, cause, cause_boxes.get(index, cause.page_boxes)))
    return changes, unexplained_shape, unexplained_color
