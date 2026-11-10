import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from image_diff.dom.parse import load_snapshot
from image_diff.generate_snapshot_test import _resolve_pr_inputs, generate_test
from image_diff.model import Box
from image_diff.snapshot_test import assert_snapshot_matches, snapshot_difference

_EXAMPLE = Path(__file__).parents[2] / "examples" / "general" / "button_enlarged" / "captures"
_BEFORE = _EXAMPLE / "before_snapshot.json"
_AFTER = _EXAMPLE / "after_snapshot.json"
_BUTTON = _EXAMPLE.parent
_BUTTON_REPORT = _BUTTON / "out" / "regression_detection" / "gemini-3.5-flash-lite" / "all" / "report_context.json"
_BUTTON_BOXES = _BUTTON / "out" / "dom" / "boxes.json"
_BUTTON_TARGETS = (((), "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"),)
_REGRESSION_CASE = Path(__file__).parents[2] / "examples" / "general" / "synthetic_five_changes"
_REGRESSION_REPORT = (
    _REGRESSION_CASE / "out" / "regression_detection" / "gemini-3.5-flash-lite" / "boxes" / "report_context.json"
)
_REGRESSION_BOXES = _REGRESSION_CASE / "out" / "dom" / "boxes.json"


def _run_generated_test(test_file: Path, snapshot: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(Path(__file__).parents[2])}
    env.pop("ACTUAL_SNAPSHOT", None)
    if snapshot is not None:
        env["ACTUAL_SNAPSHOT"] = str(snapshot)
    return subprocess.run(
        [sys.executable, "-m", "unittest", test_file.stem],
        cwd=test_file.parent,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


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

    def test_generator_uses_after_and_intended_boxes_when_no_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            generate_test(_BEFORE, _AFTER, _BUTTON_REPORT, _BUTTON_BOXES, output)

            self.assertEqual(
                output.with_name("test_generated.expected.json").read_bytes(),
                _AFTER.read_bytes(),
            )
            self.assertEqual(
                output.with_name("test_generated.actual.json").read_bytes(),
                _AFTER.read_bytes(),
            )
            source = output.read_text()
            self.assertIn("test_dom_matches_after_snapshot", source)
            self.assertIn(
                "STYLE_TARGETS = (",
                source,
            )
            self.assertIn(
                '"html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"',
                source,
            )
            self.assertIn('("padding-bottom", "padding-left", "padding-right", "padding-top"),', source)
            self.assertIn("DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).with_name", source)
            self.assertIn("actual_snapshot = Path(actual_path)", source)
            self.assertEqual(_run_generated_test(output).returncode, 0)
            mismatch = _run_generated_test(output, _BEFORE)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("FAILED (failures=1)", mismatch.stdout + mismatch.stderr)

    def test_generator_uses_before_and_regressed_boxes_when_regression_found(self):
        before = _REGRESSION_CASE / "captures" / "before_snapshot.json"
        after = _REGRESSION_CASE / "captures" / "after_snapshot.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            generate_test(before, after, _REGRESSION_REPORT, _REGRESSION_BOXES, output)

            self.assertEqual(
                output.with_name("test_generated.expected.json").read_bytes(),
                before.read_bytes(),
            )
            self.assertEqual(
                output.with_name("test_generated.actual.json").read_bytes(),
                after.read_bytes(),
            )
            source = output.read_text()
            self.assertIn("test_dom_matches_before_snapshot", source)
            self.assertIn(
                "STYLE_TARGETS = (",
                source,
            )
            self.assertIn(
                '"html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"',
                source,
            )
            self.assertIn('("background-color",),', source)
            self.assertEqual(_run_generated_test(output, before).returncode, 0)
            mismatch = _run_generated_test(output)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("FAILED (failures=1)", mismatch.stdout + mismatch.stderr)

    def test_generator_rejects_targets_without_changed_styles(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            with self.assertRaisesRegex(ValueError, "no changed CSS style"):
                generate_test(_AFTER, _AFTER, _BUTTON_REPORT, _BUTTON_BOXES, output)

    def test_targeted_snapshot_comparison_ignores_unrelated_page_changes(self):
        with tempfile.TemporaryDirectory() as directory:
            actual = Path(directory) / "actual.json"
            capture = json.loads(_AFTER.read_text())
            capture["snapshot"]["documents"][0]["contentWidth"] += 1
            actual.write_text(json.dumps(capture))

            assert_snapshot_matches(_AFTER, actual, _BUTTON_TARGETS)

    def test_targeted_snapshot_comparison_detects_target_changes(self):
        with self.assertRaisesRegex(AssertionError, "button:nth-child\\(3\\)"):
            assert_snapshot_matches(_AFTER, _BEFORE, _BUTTON_TARGETS)

    def test_style_target_comparison_ignores_unrelated_element_changes(self):
        expected = load_snapshot(_AFTER)
        key = _BUTTON_TARGETS[0]
        button = next(element for element in expected.elements if (element.frames, element.selector) == key)
        changed_button = replace(
            button,
            own_text="Different label",
            box=Box(button.box.x1 + 5, button.box.y1, button.box.x2 + 5, button.box.y2),
            styles={**button.styles, "color": "rgb(1, 2, 3)"},
        )
        actual = replace(
            expected,
            elements=tuple(changed_button if element is button else element for element in expected.elements),
        )

        self.assertIsNone(snapshot_difference(expected, actual, style_targets=((key, ("background-color",)),)))

        changed_style = replace(
            changed_button,
            styles={**changed_button.styles, "background-color": "rgb(1, 2, 3)"},
        )
        actual = replace(
            expected,
            elements=tuple(changed_style if element is button else element for element in expected.elements),
        )
        difference = snapshot_difference(expected, actual, style_targets=((key, ("background-color",)),))
        self.assertIn("style background-color", difference)

    def test_pr_lookup_uses_most_recent_dom_compatible_report(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory).resolve()
            case = repository / "cases" / "button"
            captures = case / "captures"
            output = case / "out"
            captures.mkdir(parents=True)
            (case / "pr.txt").write_text("https://github.com/example/app/pull/42\n")
            (captures / "before_snapshot.json").write_bytes(_BEFORE.read_bytes())
            (captures / "after_snapshot.json").write_bytes(_AFTER.read_bytes())
            boxes = output / "dom" / "boxes.json"
            boxes.parent.mkdir(parents=True)
            boxes.write_bytes(_BUTTON_BOXES.read_bytes())

            old_report = output / "regression_detection" / "model-a" / "all" / "report_context.json"
            latest_report = output / "regression_detection" / "model-b" / "images" / "report_baseline.json"
            pixel_report = output / "regression_detection" / "model-c" / "no_snapshots" / "report_context.json"
            for report in (old_report, latest_report, pixel_report):
                report.parent.mkdir(parents=True, exist_ok=True)
                report.write_bytes(_BUTTON_REPORT.read_bytes())
            os.utime(old_report, ns=(1_000_000_000, 1_000_000_000))
            os.utime(latest_report, ns=(2_000_000_000, 2_000_000_000))
            os.utime(pixel_report, ns=(3_000_000_000, 3_000_000_000))

            resolved = _resolve_pr_inputs(
                "https://github.com/example/app/pull/42/files?diff=split",
                repository,
            )

            self.assertEqual(
                resolved, (captures / "before_snapshot.json", captures / "after_snapshot.json", latest_report, boxes)
            )

    def test_pr_lookup_errors_when_matching_case_has_no_boxes_or_report(self):
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory).resolve()
            case = repository / "cases" / "button"
            captures = case / "captures"
            captures.mkdir(parents=True)
            (case / "pr.txt").write_text("https://github.com/example/app/pull/42")
            (captures / "before_snapshot.json").write_bytes(_BEFORE.read_bytes())
            (captures / "after_snapshot.json").write_bytes(_AFTER.read_bytes())

            with self.assertRaisesRegex(ValueError, "DOM boxes"):
                _resolve_pr_inputs("https://github.com/example/app/pull/42", repository)

            boxes = case / "out" / "dom" / "boxes.json"
            boxes.parent.mkdir(parents=True)
            boxes.write_bytes(_BUTTON_BOXES.read_bytes())
            with self.assertRaisesRegex(ValueError, "No DOM-compatible regression report"):
                _resolve_pr_inputs("https://github.com/example/app/pull/42", repository)


if __name__ == "__main__":
    unittest.main()
