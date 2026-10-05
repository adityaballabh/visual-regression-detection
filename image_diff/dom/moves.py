from collections import defaultdict

from image_diff.dom.diff import Difference, PageDiff, changed, changed_styles, resized
from image_diff.dom.match import ElementPair
from image_diff.dom.spacing import swapped_sides
from image_diff.model import SIZE_TOLERANCE_PX, Box, Cause, Element, Kind, in_reading_order

# Styles that move an element's text within its own box
_TEXT_POSITION_STYLES = ("text-align", "padding-top", "padding-right", "padding-bottom", "padding-left")
_FORM_TAGS = ("input", "textarea", "select")


def _reorder_detail(page_diff: PageDiff, pair: ElementPair, kept: list[ElementPair], position: int) -> str | None:
    flipped = []
    for index, other in enumerate(kept):
        # Keep siblings that stayed put and ended up on the other side of the mover
        if sides := swapped_sides(pair, other):
            flipped.append((abs(index - position), other, *sides))

    if not flipped:
        return None
    _, other, was, now = min(flipped, key=lambda found: found[0])
    label = page_diff.after.label(other.after)
    return f"moved from {was.relation} {label} to {now.relation} {label}"


def _kept_ids(old_ids: list[int], new_ids: list[int], distance_moved: dict[int, int]) -> set[int]:
    new_position = {sibling_id: index for index, sibling_id in enumerate(new_ids)}
    runs: list[tuple[tuple[int, int], list[int]]] = []
    for sibling_id in old_ids:
        best = (1, -distance_moved[sibling_id]), [sibling_id]

        for score, run in runs:
            longer = (score[0] + 1, score[1] - distance_moved[sibling_id])
            # Extend the longest run still in order, and when runs tie the one whose siblings moved least
            if new_position[run[-1]] < new_position[sibling_id] and longer > best[0]:
                best = longer, [*run, sibling_id]
        runs.append(best)
    return set(max(runs, key=lambda run: run[0])[1])


def reorders(page_diff: PageDiff, transformed_ids: set[int]) -> list[Cause]:
    causes = []
    for parent in page_diff.matching.pairs:
        children = [pair for pair in page_diff.matched_children(parent) if pair.before.id not in transformed_ids]
        if len(children) < 2:
            continue
        before = in_reading_order(children, lambda pair: pair.before.box)
        after = in_reading_order(children, lambda pair: pair.after.box)
        old_ids, new_ids = [pair.before.id for pair in before], [pair.before.id for pair in after]

        distance_moved = {}
        for pair in children:
            dx, dy = pair.after.box.x1 - pair.before.box.x1, pair.after.box.y1 - pair.before.box.y1
            distance_moved[pair.before.id] = abs(dx) + abs(dy)
        # Custom LCS since difflib and rapidfuzz take no tie-break, and a swap needs one to name the sibling that moved further
        kept_ids = _kept_ids(old_ids, new_ids, distance_moved)

        kept = [pair for pair in after if pair.before.id in kept_ids]
        for position, pair in enumerate(after):
            if pair.before.id in kept_ids:
                continue
            detail = _reorder_detail(page_diff, pair, kept, position)
            if detail is None:
                detail = f"moved from position {old_ids.index(pair.before.id) + 1} to {position + 1} among siblings"
            causes.append(Cause(pair.before, pair.after, Kind.SHAPE, detail, moved_itself=True))
    return causes


def reparents(page_diff: PageDiff) -> list[Cause]:
    causes = []
    for pair in page_diff.matching.pairs:
        if pair.before.parent is None or pair.after.parent is None or page_diff.parent_pair(pair):
            continue
        old_parent = page_diff.by_before.get(pair.before.parent)
        new_parent = page_diff.by_after.get(pair.after.parent)
        # Moving under a new wrapper is not a move, both parents must exist on both pages
        if old_parent is None or new_parent is None:
            continue
        was, now = page_diff.before.label(old_parent.before), page_diff.after.label(new_parent.after)
        causes.append(
            Cause(pair.before, pair.after, Kind.SHAPE, f"moved from inside {was} to inside {now}", moved_itself=True)
        )
    return causes


def transform_moves(page_diff: PageDiff) -> list[Cause]:
    causes = []
    for pair in page_diff.matching.pairs:
        before, after = pair.before.box, pair.after.box
        # Skip a transform that resized the element, since the resize reports it
        if not changed(pair, "transform") or resized(pair) or (before.x1, before.y1) == (after.x1, after.y1):
            continue

        detail = Difference("transform", pair.before.styles["transform"], pair.after.styles["transform"])
        causes.append(Cause(pair.before, pair.after, Kind.SHAPE, str(detail), moved_itself=True))
    return causes


def _text_offset(element: Element) -> tuple[int, int] | None:
    if element.text_box is None:
        return None
    return element.text_box.x1 - element.box.x1, element.text_box.y1 - element.box.y1


def _text_moved(pair: ElementPair) -> bool:
    if resized(pair) or pair.before.own_text != pair.after.own_text:
        return False
    was, now = _text_offset(pair.before), _text_offset(pair.after)
    if was is None or now is None:
        # A form control's text is not a text node, so only its text-align can show it moved
        return pair.before.tag in _FORM_TAGS and changed(pair, "text-align")
    return any(abs(old - new) > SIZE_TOLERANCE_PX for old, new in zip(was, now))


def _text_move_cause(page_diff: PageDiff, mover: ElementPair, pairs: list[ElementPair]) -> Cause:
    differences = [difference for difference in changed_styles(mover) if difference.name in _TEXT_POSITION_STYLES]
    detail = "; ".join(str(difference) for difference in differences) or "text moved within its box"

    before_box = Box.union_all(pair.before.text_box or pair.before.box for pair in pairs)
    after_box = Box.union_all(pair.after.text_box or pair.after.box for pair in pairs)
    return Cause(mover.before, mover.after, Kind.SHAPE, detail, (before_box, after_box), moved_itself=True)


def text_moves(page_diff: PageDiff) -> list[Cause]:
    moved: dict[int, list[ElementPair]] = defaultdict(list)
    for pair in page_diff.matching.pairs:
        if not _text_moved(pair):
            continue
        # Text-align is inherited, so the move belongs to the ancestor that changed it
        mover = pair if pair.before.tag in _FORM_TAGS else page_diff.inherited_from(pair, ("text-align",))
        moved[mover.before.id].append(pair)
    causes = []
    for mover_id, pairs in moved.items():
        causes.append(_text_move_cause(page_diff, page_diff.by_before[mover_id], pairs))
    return causes
