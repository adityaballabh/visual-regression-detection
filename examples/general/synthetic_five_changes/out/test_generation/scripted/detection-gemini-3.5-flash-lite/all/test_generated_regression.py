"""Generated DOM snapshot test; expected page state: before."""

import os
import unittest
from pathlib import Path

from test_generation.scripted.snapshot_assertions import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).parent / "../../../../../captures/before_snapshot.json"
DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).parent / "../../../../../captures/after_snapshot.json"
STYLE_TARGETS = (
    (
        ((), "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"),
        ("background-color",),
    ),
)


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_before_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        actual_snapshot = Path(actual_path) if actual_path else DEFAULT_ACTUAL_SNAPSHOT
        assert_snapshot_matches(EXPECTED_SNAPSHOT, actual_snapshot, style_targets=STYLE_TARGETS)


if __name__ == "__main__":
    unittest.main()
