import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from cases import reports_folder
from image_diff.dom.parse import load_snapshot
from image_diff.model import Box
from regression_detection.gemini_processor import REPO_ROOT
from test_generation.llm.generate import GenerationResult
from test_generation.scripted.generate import _save_result, generate_test
from test_generation.scripted.snapshot_assertions import assert_snapshot_matches, snapshot_difference

_EXAMPLE = REPO_ROOT / "examples" / "general" / "button_enlarged" / "captures"
_BEFORE = _EXAMPLE / "before_snapshot.json"
_AFTER = _EXAMPLE / "after_snapshot.json"
_BUTTON = _EXAMPLE.parent
_BUTTON_REPORT = _BUTTON / "out" / "regression_detection" / "gemini-3.5-flash-lite" / "all" / "report_context.json"
_BUTTON_BOXES = _BUTTON / "out" / "dom" / "boxes.json"
_BUTTON_TARGETS = (((), "html:nth-child(1) > body:nth-child(2) > section:nth-child(2) > button:nth-child(3)"),)
_REGRESSION_CASE = REPO_ROOT / "examples" / "general" / "synthetic_five_changes"
_REGRESSION_REPORT = (
    _REGRESSION_CASE / "out" / "regression_detection" / "gemini-3.5-flash-lite" / "boxes" / "report_context.json"
)
_REGRESSION_BOXES = _REGRESSION_CASE / "out" / "dom" / "boxes.json"


def _run_generated_test(test_file: Path, snapshot: Path | None = None) -> subprocess.CompletedProcess[str]:
    env = {**os.environ, "PYTHONPATH": str(REPO_ROOT)}
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


def _save_result_in(directory: str, case_folder: Path) -> Path:
    tests = Path(directory)
    report = reports_folder(case_folder, "gemini-3.5-flash-lite", "all") / "report_context.json"
    test_file = generate_test(
        case_folder / "captures" / "before_snapshot.json",
        case_folder / "captures" / "after_snapshot.json",
        report,
        case_folder / "out" / "dom" / "boxes.json",
        tests / "test_generated_regression.py",
    )
    _save_result(case_folder, "gemini-3.5-flash-lite", "all", "context", tests, test_file)
    return tests / "result.json"


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

    def test_generator_skips_when_no_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            self.assertIsNone(generate_test(_BEFORE, _AFTER, _BUTTON_REPORT, _BUTTON_BOXES, output))
            self.assertFalse(output.exists())

    def test_generator_uses_before_and_regressed_boxes_when_regression_found(self):
        before = _REGRESSION_CASE / "captures" / "before_snapshot.json"
        after = _REGRESSION_CASE / "captures" / "after_snapshot.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            generate_test(before, after, _REGRESSION_REPORT, _REGRESSION_BOXES, output)

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
            self.assertIn("DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).parent /", source)
            self.assertIn("actual_snapshot = Path(actual_path)", source)
            self.assertEqual(_run_generated_test(output, before).returncode, 0)
            mismatch = _run_generated_test(output)
            self.assertNotEqual(mismatch.returncode, 0)
            self.assertIn("FAILED (failures=1)", mismatch.stdout + mismatch.stderr)

    def test_result_records_validation_of_generated_test(self):
        with tempfile.TemporaryDirectory() as directory:
            result_file = _save_result_in(directory, _REGRESSION_CASE)
            result = GenerationResult.model_validate_json(result_file.read_text())
            self.assertEqual(result.status, "generated")
            self.assertEqual(result.flagged_box_ids, [3])
            self.assertTrue(result.attempts[0].validation.valid)
            self.assertTrue((result_file.parent / "test_generated_regression.py").exists())

    def test_result_records_skip_when_no_regression(self):
        with tempfile.TemporaryDirectory() as directory:
            result_file = _save_result_in(directory, _BUTTON)
            result = GenerationResult.model_validate_json(result_file.read_text())
            self.assertEqual(result.status, "skipped")
            self.assertIsNone(result.test_file)
            self.assertFalse((result_file.parent / "test_generated_regression.py").exists())

    def test_result_records_error_when_no_test_can_be_built(self):
        after = _REGRESSION_CASE / "captures" / "after_snapshot.json"
        with tempfile.TemporaryDirectory() as directory:
            tests = Path(directory)
            with self.assertRaises(ValueError) as caught:
                generate_test(
                    after, after, _REGRESSION_REPORT, _REGRESSION_BOXES, tests / "test_generated_regression.py"
                )
            _save_result(
                _REGRESSION_CASE, "gemini-3.5-flash-lite", "boxes", "context", tests, None, str(caught.exception)
            )
            result = GenerationResult.model_validate_json((tests / "result.json").read_text())
            self.assertEqual(result.status, "error")
            self.assertIn("no changed CSS style", result.reason)
            self.assertEqual(result.attempts, [])

    def test_generator_rejects_targets_without_changed_styles(self):
        after = _REGRESSION_CASE / "captures" / "after_snapshot.json"
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "test_generated.py"
            with self.assertRaisesRegex(ValueError, "no changed CSS style"):
                generate_test(after, after, _REGRESSION_REPORT, _REGRESSION_BOXES, output)

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


if __name__ == "__main__":
    unittest.main()
