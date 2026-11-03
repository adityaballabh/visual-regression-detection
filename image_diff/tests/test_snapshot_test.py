import json
import tempfile
import unittest
from pathlib import Path

from image_diff.generate_snapshot_test import generate_test
from image_diff.snapshot_test import assert_snapshot_matches

_EXAMPLE = Path(__file__).parents[2] / "examples" / "general" / "button_enlarged" / "captures"
_BEFORE = _EXAMPLE / "before_snapshot.json"
_AFTER = _EXAMPLE / "after_snapshot.json"


class SnapshotTestTests(unittest.TestCase):
    def test_matching_snapshots(self):
        assert_snapshot_matches(_BEFORE, _BEFORE)

    def test_mismatch_reports_page_size(self):
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual.json"
            capture = json.loads(_BEFORE.read_text())
            capture["snapshot"]["documents"][0]["contentWidth"] += 1
            actual.write_text(json.dumps(capture))

            with self.assertRaisesRegex(AssertionError, "page size"):
                assert_snapshot_matches(_BEFORE, actual)

    def test_generator_selects_requested_side(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            generate_test(_BEFORE, _AFTER, "after", output)

            self.assertEqual(
                output.with_name("test_generated.expected.json").read_bytes(),
                _AFTER.read_bytes(),
            )
            self.assertIn("test_dom_matches_after_snapshot", output.read_text())


if __name__ == "__main__":
    unittest.main()
