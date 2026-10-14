import numpy as np

from image_diff.dom.paint import explain_paint
from image_diff.model import Change, Snapshot
from image_diff.pixel.color import color_mask
from image_diff.pixel.edges import edge_mask, find_edges
from image_diff.pixel.regions import categorize_boxes, find_boxes, fit_to_edges, merge_boxes


def _pad(image: np.ndarray, height: int, width: int) -> np.ndarray:
    margins = ((0, height - image.shape[0]), (0, width - image.shape[1]), (0, 0))
    return np.pad(image, margins, constant_values=255)


def pad_to_match(before: np.ndarray, after: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Pads the bottom and right with white so both images are the same size
    height = max(before.shape[0], after.shape[0])
    width = max(before.shape[1], after.shape[1])
    return _pad(before, height, width), _pad(after, height, width)


def _numbering_key(change: Change) -> tuple[int, int]:
    # Use the after box as a fallback for added elements
    box = change.before or change.after
    return box.y1, box.x1


def diff_images(
    before: np.ndarray, after: np.ndarray, snapshots: tuple[Snapshot, Snapshot] | None = None
) -> tuple[Change, ...]:
    before_edges, after_edges = find_edges(before), find_edges(after)
    shape_boxes = find_boxes(edge_mask(before_edges, after_edges))
    color_boxes = find_boxes(color_mask(before, after))

    explained = []
    if snapshots is not None:
        explained, shape_boxes, color_boxes = explain_paint(shape_boxes, color_boxes, *snapshots)

    # Only boxes the DOM does not explain get merged
    changes = categorize_boxes(merge_boxes(shape_boxes), merge_boxes(color_boxes))
    changes = fit_to_edges(changes, before_edges, after_edges)
    return tuple(sorted(explained + changes, key=_numbering_key))
