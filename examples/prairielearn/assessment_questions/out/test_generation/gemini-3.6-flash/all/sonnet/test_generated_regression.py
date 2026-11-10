import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot

_PREFIX = (
    "html:nth-child(1) > body:nth-child(2) > div:nth-child(1) > div:nth-child(3) > "
    "div:nth-child(1) > main:nth-child(3) > div:nth-child(3) > div:nth-child(1) > "
    "div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > div:nth-child(1) > "
    "div:nth-child(2) > div:nth-child(1) > "
)
ROW_SELECTORS = [
    _PREFIX + "div:nth-child(1) > div:nth-child(2) > div:nth-child(1)",
    _PREFIX + "div:nth-child(2) > div:nth-child(2) > div:nth-child(1)",
    _PREFIX + "div:nth-child(2) > div:nth-child(3) > div:nth-child(1)",
    _PREFIX + "div:nth-child(2) > div:nth-child(4) > div:nth-child(1)",
]
EXPECTED_PADDING_RIGHT = 24.0  # from the BEFORE snapshot (1.5rem)


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))

    def _find(self, selector):
        for el in self.snapshot.elements:
            if el.selector == selector and not el.frames:
                return el
        self.fail(f"{selector}: element not found in snapshot")

    def test_question_rows_keep_right_padding(self):
        """Guards against question rows losing their right inner gap.

        The change to the assessment question tree rows dropped
        `padding-right:1.5rem` (24px -> 0px), so the right-aligned points text
        touches/clips at the row's right edge.
        """
        for selector in ROW_SELECTORS:
            el = self._find(selector)
            raw = el.styles.get("padding-right")
            try:
                actual = float(str(raw).replace("px", ""))
            except (TypeError, ValueError):
                self.fail(f"{selector}: padding-right unreadable, got {raw!r}")
            if abs(actual - EXPECTED_PADDING_RIGHT) > 1:
                self.fail(f"{selector}: property padding-right expected {EXPECTED_PADDING_RIGHT:g}px but got {raw}")


if __name__ == "__main__":
    unittest.main()
