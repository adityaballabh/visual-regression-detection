"""Generated DOM snapshot test; expected page state: after."""

import os
import unittest
from pathlib import Path

from image_diff.snapshot_test import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).with_name("test_button_snapshot.expected.json")
DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).parents[2] / "examples/general/button_enlarged/captures/after_snapshot.json"


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_after_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        actual_snapshot = Path(actual_path) if actual_path else DEFAULT_ACTUAL_SNAPSHOT
        assert_snapshot_matches(EXPECTED_SNAPSHOT, actual_snapshot)


if __name__ == "__main__":
    unittest.main()
