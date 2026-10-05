from statistics import mode

from image_diff.dom.diff import PageDiff, resized, size_changes
from image_diff.dom.match import ElementPair
from image_diff.model import Box, Cause, Edge, overlapping, px


def _margin_change(pair: ElementPair, side: str) -> float:
    before, after = pair
    return px(after.styles.get(f"margin-{side}", "0px")) - px(before.styles.get(f"margin-{side}", "0px"))


def _stationary_x(page_diff: PageDiff, pair: ElementPair) -> str:
    parent = page_diff.parent_pair(pair)
    placement = parent.after.styles if parent else {}
    justify, align = placement.get("justify-content"), placement.get("text-align")
    left_change, right_change = _margin_change(pair, "left"), _margin_change(pair, "right")
    # Growth keeps the center, the right edge or the left edge still, depending on how the element is aligned
    if justify in ("center", "space-around", "space-evenly") or align == "center" or left_change == right_change != 0:
        return "center"
    if justify in ("flex-end", "end", "right") or align in ("right", "end") or (left_change != 0 and right_change == 0):
        return "right"
    return "left"


def _edge_x(box: Box, stationary: str) -> int:
    if stationary == "center":
        return (box.x1 + box.x2) // 2
    return box.edge(stationary)


def _push(page_diff: PageDiff, pair: ElementPair) -> tuple[int, int]:
    before, after = pair.before.box, pair.after.box
    stationary = _stationary_x(page_diff, pair)
    # Measure on the edge growth does not move, so only a push by something else counts
    dx = _edge_x(after, stationary) - _edge_x(before, stationary)
    dy = after.y1 - before.y1
    # Subtract the element's own margin change, unless it resized, since then the margin is probably auto
    changed_sizes = {difference.name for difference in size_changes(pair)}
    if "width" not in changed_sizes:
        dx -= round(_margin_change(pair, "left"))
    if "height" not in changed_sizes:
        dy -= round(_margin_change(pair, "top"))
    return dx, dy


def _moves(dx: int, dy: int) -> list[tuple[Edge, int]]:
    # How far a corner moved toward each side
    toward = {Edge.TOP: -dy, Edge.RIGHT: dx, Edge.BOTTOM: dy, Edge.LEFT: -dx}
    return [(side, distance) for side, distance in toward.items() if distance > 0]


def _shift_note(moves: list[tuple[Edge, int]]) -> str:
    steps = []
    for side in Edge:
        distances = [distance for moved_side, distance in moves if moved_side == side]
        # Note the most common distance toward each side
        if distances:
            steps.append(f"{mode(distances)}px {side.direction}")
    return "content moved " + ", ".join(steps)


def _origin_box(cause: Cause) -> Box:
    # Where the cause was, or where it appeared for an added element
    before_box, after_box = cause.page_boxes
    return before_box or after_box


def _pushes_along(page_diff: PageDiff, cause: Cause, vertical: bool) -> bool:
    if cause.boxes:
        before_box, after_box = cause.boxes
        # A gap or moved text pushes along the axis its box changed size on
        return before_box.height != after_box.height if vertical else before_box.width != after_box.width

    # An added or removed element pushes along both axes
    if cause.before is None or cause.after is None:
        return True
    pair = page_diff.by_before[cause.before.id]

    # A swap or reparent pushes along the axis it moved on, since the element keeps its size
    if cause.moved_itself:
        dx, dy = _push(page_diff, pair)
        return dy != 0 if vertical else dx != 0
    if not resized(pair):
        return True

    # A resize pushes along the axis it or an ancestor grew on, like a nav that gets taller when its links wrap
    changed_sizes = set()
    for element in (pair.after, *page_diff.after.ancestors_of(pair.after)):
        if element_pair := page_diff.by_after.get(element.id):
            changed_sizes.update(difference.name for difference in size_changes(element_pair))
    return ("height" if vertical else "width") in changed_sizes


def _pusher(page_diff: PageDiff, causes: list[Cause], pair: ElementPair, vertical: bool) -> int | None:
    box = pair.before.box
    candidates = []
    for index, cause in enumerate(causes):
        itself = cause.before is not None and cause.before.id == pair.before.id
        if itself or not _pushes_along(page_diff, cause, vertical):
            continue

        origin = _origin_box(cause)
        # A push up or down comes from above, a push sideways comes from the same row
        if vertical:
            placed_to_push = origin.y1 < box.y1
        else:
            placed_to_push = overlapping(origin.y1, origin.y2, box.y1, box.y2)

        if placed_to_push:
            candidates.append(index)
    if not candidates:
        return None

    # Credit the nearest cause along the axis of the push
    def distance(index: int) -> int:
        origin = _origin_box(causes[index])
        if vertical:
            return box.y1 - origin.y2
        return origin.horizontal_gap(box)

    return min(candidates, key=distance)


def _cause_push(page_diff: PageDiff, causes: list[Cause], cause: Cause) -> tuple[int, int]:
    # Only a resize or a gap is pushed by others
    if cause.before is None or cause.after is None or cause.moved_itself:
        return 0, 0
    pair = page_diff.by_before[cause.before.id]
    dx, dy = _push(page_diff, pair)
    # Movement no cause accounts for, such as a flex row rebalancing, is not a push
    if _pusher(page_diff, causes, pair, vertical=False) is None:
        dx = 0
    if _pusher(page_diff, causes, pair, vertical=True) is None:
        dy = 0
    return dx, dy


def with_shifts(causes: list[Cause], page_diff: PageDiff) -> tuple[list[Cause], set[int]]:
    before_ids = {cause.before.id for cause in causes if cause.before}
    self_moved_ids = {cause.before.id for cause in causes if cause.before and cause.moved_itself}
    moves: list[list[tuple[Edge, int]]] = [[] for _ in causes]

    # Before page ids of the elements whose move was credited to a cause
    shifted_ids = set()
    for pair in page_diff.matching.pairs:
        dx, dy = _push(page_diff, pair)
        # Skip causes that moved themselves and content inside a cause
        if page_diff.before.is_inside(pair.before, before_ids) or pair.before.id in self_moved_ids:
            continue

        for vertical, distance in ((False, dx), (True, dy)):
            pusher = _pusher(page_diff, causes, pair, vertical) if distance else None
            if pusher is None:
                continue
            # Measure the shift relative to the cause, since the cause might have been pushed too
            cause_dx, cause_dy = _cause_push(page_diff, causes, causes[pusher])
            moves[pusher] += _moves(0, distance - cause_dy) if vertical else _moves(distance - cause_dx, 0)
            shifted_ids.add(pair.before.id)

    noted = []
    for cause, cause_moves in zip(causes, moves):
        detail = f"{cause.detail}. {_shift_note(cause_moves)}" if cause_moves else cause.detail
        noted.append(cause._replace(detail=detail))
    return noted, shifted_ids
