import numpy as np

from image_diff.model import Box
from image_diff.pixel.color import color_mask
from image_diff.pixel.regions import find_boxes, merge_boxes


def _pad(image: np.ndarray, height: int, width: int) -> np.ndarray:
    margins = ((0, height - image.shape[0]), (0, width - image.shape[1]), (0, 0))
    return np.pad(image, margins, constant_values=255)


def pad_to_match(before: np.ndarray, after: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    # Pads the bottom and right with white so both images are the same size
    height = max(before.shape[0], after.shape[0])
    width = max(before.shape[1], after.shape[1])
    return _pad(before, height, width), _pad(after, height, width)


def diff_images(before: np.ndarray, after: np.ndarray) -> tuple[Box, ...]:
    mask = color_mask(before, after)
    boxes = merge_boxes(find_boxes(mask))
    return tuple(sorted(boxes, key=lambda box: (box.y1, box.x1)))
