# Adapted from X-PERT (Choudhary, Prasad & Orso, 2013)

from collections import defaultdict

from image_diff.dom.diff import (
    Difference,
    PageDiff,
    change_kind,
    changed_styles,
    matches_any,
    resized,
    same_change,
    size_changes,
)
from image_diff.dom.match import ElementPair
from image_diff.dom.moves import reorders, reparents, text_moves
from image_diff.dom.shift_notes import with_shifts
from image_diff.dom.spacing import Claim, Gap, changed_gaps, owner
from image_diff.model import Box, Cause, Element, Kind, Snapshot

# Layout triggering CSS properties except positions and used values, since these set an element's own size
_SIZE_STYLES = [
    "font-*", "letter-spacing", "word-spacing", "line-height", "text-indent", "text-transform", "white-space",
    "box-sizing", "padding-*", "border-*-width", "min-*", "max-*", "flex-basis", "flex-grow", "flex-shrink", "overflow-*",
]  # fmt: skip
_DISTRIBUTING = ("flex", "inline-flex", "grid", "inline-grid")


def _subtree_tops(snapshot: Snapshot, elements: tuple[Element, ...]) -> list[Element]:
    ids = {element.id for element in elements}
    tops = []
    for element in elements:
        # Report a whole added or removed subtree once, on its outermost element
        if not snapshot.is_inside(element, ids):
            tops.append(element)
    return tops


def _size_style_differences(page_diff: PageDiff, pair: ElementPair) -> list[Difference]:
    parent = page_diff.parent_pair(pair)
    differences = []
    for difference in changed_styles(pair):
        if not matches_any(difference.name, _SIZE_STYLES):
            continue
        # Skip styles the parent changed the same way since the element inherited them
        if parent and same_change(pair, parent, difference.name):
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
    detail = "; ".join(str(difference) for difference in (*differences, *size_changes(pair)))
    return Cause(pair.before, pair.after, change_kind(differences), detail)


def _gap_causes(blamed: list[tuple[Claim, Gap]]) -> list[Cause]:
    # Group by element since one element's margin or padding can change the gaps on several sides
    groups: dict[int, list[tuple[Claim, Gap]]] = defaultdict(list)
    for claim, gap in blamed:
        groups[claim.pair.before.id].append((claim, gap))
    causes = []
    for group in groups.values():
        details: dict[str, str] = {}
        for claim, gap in group:
            details.setdefault(claim.label, f"{claim.label} {gap.was}px -> {gap.now}px")

        pair = group[0][0].pair
        before_box = Box.union_all(gap.before_box for _, gap in group)
        after_box = Box.union_all(gap.after_box for _, gap in group)
        causes.append(
            Cause(
                pair.before,
                pair.after,
                Kind.SHAPE,
                "; ".join(details.values()),
                (before_box, after_box),
            )
        )
    return causes


class _PageAccountedFor:
    def __init__(self, snapshot: Snapshot):
        self.snapshot = snapshot
        self.ids: set[int] = set()
        # Ancestors of claimed elements, which grew or shrank around them
        self.holder_ids: set[int] = set()

    def add(self, element: Element):
        self.ids.add(element.id)
        self.holder_ids.update(ancestor.id for ancestor in self.snapshot.ancestors_of(element))

    def has_accounted_child(self, element: Element) -> bool:
        return any(self.snapshot.elements[claimed].parent == element.id for claimed in self.ids)

    def explains(self, element: Element) -> bool:
        if element.id in self.holder_ids or self.snapshot.is_inside(element, self.ids):
            return True
        # A flex or grid parent hands a claimed child's space change on to its siblings
        parent = self.snapshot.elements[element.parent] if element.parent is not None else None
        if parent is None or parent.styles.get("display") not in _DISTRIBUTING:
            return False
        return self.has_accounted_child(parent)


class _AccountedFor:
    def __init__(self, page_diff: PageDiff):
        self.before = _PageAccountedFor(page_diff.before)
        self.after = _PageAccountedFor(page_diff.after)

    def add(self, before: Element | None, after: Element | None):
        if before:
            self.before.add(before)
        if after:
            self.after.add(after)

    def explains(self, pair: ElementPair) -> bool:
        return self.before.explains(pair.before) or self.after.explains(pair.after)

    def redistributed(self, gap: Gap, resized_ids: set[int]) -> bool:
        container = gap.container
        # The container resized or a child did, so its layout moved the space around
        if container.before.id in self.before.ids and resized(container):
            return True
        if self.before.has_accounted_child(container.before) or self.after.has_accounted_child(container.after):
            return True
        return any(child.id in resized_ids for child in self.before.snapshot.children_of(container.before))


def _unexplained_resizes(unowned_resizes: list[ElementPair], accounted_for: _AccountedFor) -> list[ElementPair]:
    settled = False
    # Explaining one resize can explain its children and siblings, so repeat until a pass accounts for nothing new
    while not settled:
        settled = True
        for pair in list(unowned_resizes):
            if accounted_for.explains(pair):
                accounted_for.add(*pair)
                unowned_resizes.remove(pair)
                settled = False
    return unowned_resizes


def _without_holders(pairs: list[ElementPair], snapshot: Snapshot) -> list[ElementPair]:
    holder_ids = set()
    for pair in pairs:
        holder_ids.update(ancestor.id for ancestor in snapshot.ancestors_of(pair.before))
    return [pair for pair in pairs if pair.before.id not in holder_ids]


def _claimed_gaps(
    page_diff: PageDiff, gaps: list[Gap], moved_text_ids: set[int]
) -> tuple[list[tuple[Claim, Gap]], list[Gap]]:
    claimed, unclaimed = [], []
    for gap in gaps:
        claim = owner(gap)
        # Skip a margin claim on an unowned resize, since Chromium reports an auto margin as the space left over
        follows_resize = claim and claim.is_margin and resized(claim.pair) and not _owns_resize(page_diff, claim.pair)
        if claim is None or follows_resize:
            unclaimed.append(gap)
        elif claim.pair.before.id not in moved_text_ids:
            claimed.append((claim, gap))
    return claimed, unclaimed


def _known_causes(page_diff: PageDiff) -> tuple[list[Cause], list[ElementPair], list[Gap]]:
    before, after, matching = page_diff.before, page_diff.after, page_diff.matching
    causes = []
    for element in _subtree_tops(before, matching.removed):
        causes.append(Cause(element, None, Kind.SHAPE, "removed"))
    for element in _subtree_tops(after, matching.added):
        causes.append(Cause(None, element, Kind.SHAPE, "added"))
    text_move_causes = text_moves(page_diff)
    causes += reorders(page_diff) + reparents(page_diff) + text_move_causes

    moved_text_ids = {cause.before.id for cause in text_move_causes}
    claimed, unclaimed_gaps = _claimed_gaps(page_diff, changed_gaps(page_diff), moved_text_ids)
    gap_causes = _gap_causes(claimed)
    spaced_ids = {cause.before.id for cause in gap_causes}
    causes += gap_causes

    unowned_resizes = []
    for pair in page_diff.matching.pairs:
        if not resized(pair):
            continue
        if not _owns_resize(page_diff, pair):
            unowned_resizes.append(pair)
        # Padding that grew is already reported as the inset it changed
        elif pair.before.id not in spaced_ids:
            causes.append(_resize(page_diff, pair))
    return causes, unowned_resizes, unclaimed_gaps


def _leftover_causes(
    page_diff: PageDiff, known: list[Cause], unowned_resizes: list[ElementPair], unclaimed_gaps: list[Gap]
) -> list[Cause]:
    accounted_for = _AccountedFor(page_diff)
    for cause in known:
        accounted_for.add(cause.before, cause.after)
    resized_ids = {pair.before.id for pair in page_diff.matching.pairs if resized(pair)}

    causes = []
    # Blame a gap nothing rearranged on its fallback and a resize nothing explains on itself, until nothing is left
    while True:
        unowned_resizes = _unexplained_resizes(unowned_resizes, accounted_for)
        standalone_gaps = [gap for gap in unclaimed_gaps if not accounted_for.redistributed(gap, resized_ids)]
        unclaimed_gaps = [gap for gap in unclaimed_gaps if accounted_for.redistributed(gap, resized_ids)]
        if standalone_gaps:
            found = _gap_causes([(gap.fallback, gap) for gap in standalone_gaps])
        elif unowned_resizes:
            found = [_resize(page_diff, pair) for pair in _without_holders(unowned_resizes, page_diff.before)]
            found_ids = {cause.before.id for cause in found}
            unowned_resizes = [pair for pair in unowned_resizes if pair.before.id not in found_ids]
        else:
            return causes
        causes += found
        for cause in found:
            accounted_for.add(cause.before, cause.after)


def explain_layout(page_diff: PageDiff) -> tuple[list[Cause], set[int]]:
    causes, unowned_resizes, unclaimed_gaps = _known_causes(page_diff)
    causes += _leftover_causes(page_diff, causes, unowned_resizes, unclaimed_gaps)
    return with_shifts(causes, page_diff)
