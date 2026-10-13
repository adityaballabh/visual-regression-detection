import cv2
import numpy as np

# Anti-aliased edges shift by a pixel between renders
TOLERANCE_PX = 1
# Canny hysteresis thresholds
_CANNY_LOW = 50
_CANNY_HIGH = 150


def find_edges(image: np.ndarray) -> np.ndarray:
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    return cv2.Canny(gray, _CANNY_LOW, _CANNY_HIGH) > 0


def _widen(edges: np.ndarray) -> np.ndarray:
    size = 2 * TOLERANCE_PX + 1
    kernel = np.ones((size, size), np.uint8)
    return cv2.dilate(edges.astype(np.uint8), kernel) > 0


def edge_mask(before_edges: np.ndarray, after_edges: np.ndarray) -> np.ndarray:
    # Edges in an image that have no edge within TOLERANCE_PX in the other
    appeared = after_edges & ~_widen(before_edges)
    disappeared = before_edges & ~_widen(after_edges)
    return appeared | disappeared
