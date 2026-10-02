from functools import reduce

import cv2
import numpy as np

from image_diff.model import Box

# Morphological closing radius for joining nearby changed pixels
_CLOSE_RADIUS_PX = 4
# Boxes closer than this are one change
_MERGE_GAP_PX = 8
# Patches with fewer changed pixels than this are ignored
_MIN_PIXELS = 9


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
    for x, y, width, height, pixels in stats[1:count]:
        if pixels >= _MIN_PIXELS:
            boxes.append(Box(int(x), int(y), int(x + width), int(y + height)))
    return boxes
