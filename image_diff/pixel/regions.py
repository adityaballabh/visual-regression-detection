from functools import reduce

import cv2
import numpy as np

from image_diff.model import Box, Change, Kind

# Morphological closing radius for joining nearby changed pixels
_CLOSE_RADIUS_PX = 4
# Boxes closer than this are one change
_MERGE_GAP_PX = 8


def merge_boxes(boxes: list[Box]) -> list[Box]:
    merged: list[Box] = []
    pending = list(boxes)
    while pending:
        box = pending.pop()
        nearby_boxes = [other for other in merged if other.is_near(box, _MERGE_GAP_PX)]
        if not nearby_boxes:
            merged.append(box)
            continue

        merged = [other for other in merged if other not in nearby_boxes]
        nearby_combined = reduce(Box.union, nearby_boxes, box)
        # The combined box might be close to boxes its parts were not
        pending.append(nearby_combined)
    return merged


def find_boxes(mask: np.ndarray) -> list[Box]:
    size = 2 * _CLOSE_RADIUS_PX + 1
    kernel = np.ones((size, size), np.uint8)
    closed = cv2.morphologyEx(mask.astype(np.uint8), cv2.MORPH_CLOSE, kernel)
    count, _, stats, _ = cv2.connectedComponentsWithStats(closed)

    boxes = []
    # Skip row 0 since it's the background
    for x, y, width, height, _ in stats[1:count]:
        boxes.append(Box(int(x), int(y), int(x + width), int(y + height)))
    return boxes


def _touches_any(box: Box, others: list[Box]) -> bool:
    return any(box.is_near(other, 0) for other in others)


def categorize_boxes(shape_boxes: list[Box], color_boxes: list[Box]) -> list[Change]:
    # Color boxes touching a shape box belong to that change
    absorbed = [box for box in color_boxes if _touches_any(box, shape_boxes)]
    shape_boxes = merge_boxes(shape_boxes + absorbed)
    color_boxes = [box for box in color_boxes if box not in absorbed]

    changes = [Change(box, box, Kind.SHAPE) for box in shape_boxes]
    changes += [Change(box, box, Kind.COLOR) for box in color_boxes]
    return changes


def _edge_extent(edges: np.ndarray, region: Box) -> Box | None:
    ys, xs = np.nonzero(edges[region.y1 : region.y2, region.x1 : region.x2])
    if len(xs) == 0:
        return None
    return Box(
        region.x1 + int(xs.min()),
        region.y1 + int(ys.min()),
        region.x1 + int(xs.max()) + 1,
        region.y1 + int(ys.max()) + 1,
    )


def fit_to_edges(changes: list[Change], before_edges: np.ndarray, after_edges: np.ndarray) -> list[Change]:
    # Shrink each side of a shape change to its own edges
    fitted = []
    for change in changes:
        if change.kind == Kind.SHAPE:
            # Both sides currently hold the same unfitted region
            region = change.before
            before = _edge_extent(before_edges, region)
            after = _edge_extent(after_edges, region)
            change = Change(before, after, Kind.SHAPE)
        fitted.append(change)
    return fitted
