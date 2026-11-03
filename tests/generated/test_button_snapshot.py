"""Generated DOM snapshot test; expected page state: after."""

import os
import unittest
from pathlib import Path

from image_diff.snapshot_test import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).with_name('test_button_snapshot.expected.json')


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_after_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        self.assertTrue(actual_path, "Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        assert_snapshot_matches(EXPECTED_SNAPSHOT, Path(actual_path))


if __name__ == "__main__":
    unittest.main()
