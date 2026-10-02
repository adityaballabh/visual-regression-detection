import cv2
import numpy as np
from skimage.color import deltaE_ciede2000

# Roughly where color changes become noticeable
_DELTA_E = 3.0
# Anti-aliased edges shift by a pixel between renders
_TOLERANCE_PX = 1


def _to_lab(image: np.ndarray) -> np.ndarray:
    return cv2.cvtColor(image.astype(np.float32) / 255, cv2.COLOR_BGR2Lab)


def color_mask(before: np.ndarray, after: np.ndarray) -> np.ndarray:
    before_lab, after_lab = _to_lab(before), _to_lab(after)
    height, width = before.shape[:2]

    ys, xs = np.nonzero(deltaE_ciede2000(before_lab, after_lab) > _DELTA_E)
    changed = np.ones(len(ys), dtype=bool)

    # Anti-aliasing fix
    for dy in range(-_TOLERANCE_PX, _TOLERANCE_PX + 1):
        for dx in range(-_TOLERANCE_PX, _TOLERANCE_PX + 1):
            neighbor_ys = np.clip(ys + dy, 0, height - 1)
            neighbor_xs = np.clip(xs + dx, 0, width - 1)
            neighbor_differs = deltaE_ciede2000(before_lab[neighbor_ys, neighbor_xs], after_lab[ys, xs]) > _DELTA_E
            changed &= neighbor_differs

    mask = np.zeros((height, width), dtype=bool)
    mask[ys[changed], xs[changed]] = True
    return mask
