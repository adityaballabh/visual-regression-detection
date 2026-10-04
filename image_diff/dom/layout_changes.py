# Adapted from X-PERT (Choudhary, Prasad & Orso, 2013)

from statistics import mode
from typing import NamedTuple

from image_diff.dom.diff import Difference, PageDiff, change_kind, changed_styles, matches_any
from image_diff.dom.match import ElementPair
from image_diff.model import Box, Element, Kind, Snapshot

# Edges round separately on each page, so a size can drift a pixel with nothing changed
_SIZE_TOLERANCE_PX = 1
# Layout triggering CSS properties except positions and used values, since these set an element's own size
_SIZE_STYLES = [
    "font-*", "letter-spacing", "word-spacing", "line-height", "text-indent", "text-transform", "white-space",
    "box-sizing", "padding-*", "border-*-width", "min-*", "max-*", "flex-basis", "flex-grow", "flex-shrink", "overflow-*",
]  # fmt: skip
_DISTRIBUTING = ("flex", "inline-flex", "grid", "inline-grid")
# Words for the shift note, in CSS side order
_DIRECTION_WORDS = {"top": "up", "right": "right", "bottom": "down", "left": "left"}


class Cause(NamedTuple):
    # None on a page where the element does not exist
    before: Element | None
    after: Element | None
    kind: Kind
    detail: str


def _subtree_tops(snapshot: Snapshot, elements: tuple[Element, ...]) -> list[Element]:
    visible_ids = {element.id for element in elements if element.visible}
    tops = []
    for element in elements:
        # Report a whole added or removed subtree once, on its outermost element
        if element.id in visible_ids and not snapshot.is_inside(element, visible_ids):
            tops.append(element)
    return tops


def _visible_pairs(page_diff: PageDiff) -> list[ElementPair]:
    return [pair for pair in page_diff.matching.pairs if pair.before.visible and pair.after.visible]


def _size_changes(pair: ElementPair) -> list[Difference]:
    before, after = pair.before.box, pair.after.box
    sizes = (("width", before.width, after.width), ("height", before.height, after.height))
    changes = []
    for name, was, now in sizes:
        if abs(now - was) > _SIZE_TOLERANCE_PX:
            changes.append(Difference(name, f"{was}px", f"{now}px"))
    return changes


def _resized(pair: ElementPair) -> bool:
    return bool(_size_changes(pair))


def _size_style_differences(page_diff: PageDiff, pair: ElementPair) -> list[Difference]:
    parent = page_diff.parent_pair(pair)
    differences = []
    for difference in changed_styles(pair):
        name, was, now = difference
        if not matches_any(name, _SIZE_STYLES):
            continue
        # Skip styles the parent changed the same way since the element inherited them
        if parent and (parent.before.styles.get(name), parent.after.styles.get(name)) == (was, now):
            continue
        differences.append(difference)
    return differences


def _owns_resize(page_diff: PageDiff, pair: ElementPair) -> bool:
    return pair.before.own_text != pair.after.own_text or bool(_size_style_differences(page_diff, pair))


def _resize(page_diff: PageDiff, pair: ElementPair) -> Cause:
    differences = page_diff.own_differences(pair)
    shown = {difference.name for difference in differences}
    for difference in _size_style_differences(page_diff, pair):
        # Add padding and line height since the paint differences leave them out
        if difference.name not in shown:
            differences.append(difference)
    detail = "; ".join(str(difference) for difference in (*differences, *_size_changes(pair)))
    return Cause(pair.before, pair.after, change_kind(differences), detail)


class _PageClaims:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot
        self.ids: set[int] = set()
        # Ancestors of claimed elements, which grew or shrank around them
        self.holder_ids: set[int] = set()

    def add(self, element: Element):
        self.ids.add(element.id)
        self.holder_ids.update(ancestor.id for ancestor in self.snapshot.ancestors_of(element))

    def explains(self, element: Element) -> bool:
        if element.id in self.holder_ids or self.snapshot.is_inside(element, self.ids):
            return True
        # A flex or grid parent hands a claimed child's space change on to its siblings
        parent = self.snapshot.elements[element.parent] if element.parent is not None else None
        if parent is None or parent.styles.get("display") not in _DISTRIBUTING:
            return False
        return any(self.snapshot.elements[claimed].parent == parent.id for claimed in self.ids)


class _Claims:
    def __init__(self, page_diff: PageDiff):
        self.before = _PageClaims(page_diff.before)
        self.after = _PageClaims(page_diff.after)

    def add(self, before: Element | None, after: Element | None):
        if before:
            self.before.add(before)
        if after:
            self.after.add(after)

    def explains(self, pair: ElementPair) -> bool:
        return self.before.explains(pair.before) or self.after.explains(pair.after)


def _unexplained(pending: list[ElementPair], claims: _Claims) -> list[ElementPair]:
    settled = False
    # Explaining one resize can explain its children and siblings, so repeat until a pass claims nothing
    while not settled:
        settled = True
        for pair in list(pending):
            if claims.explains(pair):
                claims.add(*pair)
                pending.remove(pair)
                settled = False
    return pending


def _without_holders(pairs: list[ElementPair], snapshot: Snapshot) -> list[ElementPair]:
    holder_ids = set()
    for pair in pairs:
        holder_ids.update(ancestor.id for ancestor in snapshot.ancestors_of(pair.before))
    return [pair for pair in pairs if pair.before.id not in holder_ids]


def _push(before: Box | None, after: Box | None) -> tuple[int, int]:
    if before is None or after is None:
        return 0, 0
    dx, dy = after.x1 - before.x1, after.y1 - before.y1
    # A centered element's corner moves when it widens, so only count sideways movement at the same width
    if before.width != after.width:
        dx = 0
    return dx, dy


def _moves(dx: int, dy: int) -> list[tuple[str, int]]:
    # How far a corner moved toward each side
    toward = {"top": -dy, "right": dx, "bottom": dy, "left": -dx}
    return [(side, distance) for side, distance in toward.items() if distance > 0]


def _shift_note(moves: list[tuple[str, int]]) -> str:
    steps = []
    for side, word in _DIRECTION_WORDS.items():
        distances = [distance for moved_side, distance in moves if moved_side == side]
        # Note the most common distance toward each side
        if distances:
            steps.append(f"{mode(distances)}px {word}")
    return "content moved " + ", ".join(steps)


def _cause_box(cause: Cause) -> Box:
    return cause.after.box if cause.after else cause.before.box


def _with_shifts(causes: list[Cause], page_diff: PageDiff) -> list[Cause]:
    before_ids = {cause.before.id for cause in causes if cause.before}
    moves: list[list[tuple[str, int]]] = [[] for _ in causes]
    for pair in _visible_pairs(page_diff):
        dx, dy = _push(pair.before.box, pair.after.box)
        # Skip content inside a cause, it moved because the cause grew around it
        if (dx, dy) == (0, 0) or page_diff.before.is_inside(pair.before, before_ids):
            continue
        # A cause can be shifted by another cause but not by itself
        others = [
            index for index, cause in enumerate(causes) if cause.before is None or cause.before.id != pair.before.id
        ]
        if not others:
            continue
        nearest = min(others, key=lambda index: _cause_box(causes[index]).manhattan_distance(pair.before.box))
        cause = causes[nearest]
        # Measure the shift relative to the cause, since the cause might have been pushed too
        cause_dx, cause_dy = _push(cause.before and cause.before.box, cause.after and cause.after.box)
        moves[nearest] += _moves(dx - cause_dx, dy - cause_dy)

    noted = []
    for cause, cause_moves in zip(causes, moves):
        detail = f"{cause.detail}. {_shift_note(cause_moves)}" if cause_moves else cause.detail
        noted.append(cause._replace(detail=detail))
    return noted


def explain_layout(page_diff: PageDiff) -> list[Cause]:
    before, after, matching = page_diff.before, page_diff.after, page_diff.matching
    causes = []
    for element in _subtree_tops(before, matching.removed):
        causes.append(Cause(element, None, Kind.SHAPE, "removed"))
    for element in _subtree_tops(after, matching.added):
        causes.append(Cause(None, element, Kind.SHAPE, "added"))

    pending = []
    for pair in _visible_pairs(page_diff):
        if not _resized(pair):
            continue
        if _owns_resize(page_diff, pair):
            causes.append(_resize(page_diff, pair))
        else:
            pending.append(pair)

    claims = _Claims(page_diff)
    for cause in causes:
        claims.add(cause.before, cause.after)

    # Report an unexplained resize as its own cause
    while pending := _unexplained(pending, claims):
        for pair in _without_holders(pending, before):
            causes.append(_resize(page_diff, pair))
            claims.add(*pair)
            pending.remove(pair)
    return _with_shifts(causes, page_diff)
