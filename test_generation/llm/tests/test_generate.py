import json
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path

from regression_detection.gemini_processor import RegressionReport
from test_generation.llm import generate as generation

_EXAMPLE = generation.REPO_ROOT / "examples" / "general" / "synthetic_five_changes"
_MODEL = "gemini-3.5-flash-lite"
_REPORT = Path("out") / "regression_detection" / _MODEL / "all" / "report_context.json"
_SELECTOR = "html:nth-child(1) > body:nth-child(2) > section:nth-child(3) > div:nth-child(2)"

_GOOD_TEST = f'''
import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class T(unittest.TestCase):
    def test_card_is_green(self):
        snapshot = load_snapshot(Path(os.environ["ACTUAL_SNAPSHOT"]))
        card = next(e for e in snapshot.elements if e.selector == "{_SELECTOR}")
        self.assertEqual(card.styles["background-color"], "rgb(220, 252, 231)", "{_SELECTOR} background-color")
'''
# Passes on both snapshots, so it does not catch the regression
_NEVER_FAILS = "import unittest\n\n\nclass T(unittest.TestCase):\n    def test_nothing(self):\n        pass\n"
_CRASHES = "raise RuntimeError('broken test')\n"


def _stub_claude(folder: Path, tests: list[str]) -> Path:
    """A stand-in for the claude command that writes the next test in the list and prints a JSON result."""
    script = folder / "claude"
    script.write_text(
        f"#!{sys.executable}\n"
        "import json, sys\n"
        "from pathlib import Path\n"
        "if '--version' in sys.argv:\n"
        "    sys.exit(print('stub'))\n"
        f"tests = {tests!r}\n"
        f"counter = Path({str(folder / 'calls')!r})\n"
        "call = int(counter.read_text()) if counter.exists() else 0\n"
        "counter.write_text(str(call + 1))\n"
        "sys.stdin.read()\n"
        f"Path({generation.TEST_FILE!r}).write_text(tests[min(call, len(tests) - 1)])\n"
        "print(json.dumps({'result': 'ok', 'is_error': False, 'num_turns': 2, 'total_cost_usd': 0.5, 'duration_ms': 10,"
        " 'session_id': 's', 'usage': {'input_tokens': 10, 'cache_creation_input_tokens': 20,"
        " 'cache_read_input_tokens': 30, 'output_tokens': 40}}))\n"
    )
    script.chmod(script.stat().st_mode | stat.S_IEXEC)
    return script


class TestGeneration(unittest.TestCase):
    def setUp(self):
        self.folder = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.folder)
        self.case = self.folder / "case"
        shutil.copytree(_EXAMPLE, self.case, ignore=shutil.ignore_patterns("test_generation"))

    def _generate(self, tests: list[str], **options):
        claude = _stub_claude(self.folder, tests)
        return generation.generate_test(self.case, claude_bin=str(claude), cache_dir=self.folder / "cache", **options)

    def test_usage_is_read_from_the_agent_output(self):
        usage = generation._usage_from(
            {"total_cost_usd": 0.25, "num_turns": 3, "usage": {"input_tokens": 5, "output_tokens": 7}}
        )
        self.assertEqual(
            (usage.input_tokens, usage.output_tokens, usage.total_cost_usd, usage.num_turns), (5, 7, 0.25, 3)
        )
        self.assertEqual((usage + usage).output_tokens, 14)

    def test_flagged_boxes_keep_the_selector_and_the_reason(self):
        report = RegressionReport.model_validate_json((self.case / _REPORT).read_text())
        (box,) = generation._flagged_boxes(self.case, "all", report)
        self.assertEqual((box["id"], box["selector"], box["category"]), (3, _SELECTOR, "color"))

    def test_valid_test_is_generated_and_usage_recorded(self):
        result = self._generate([_GOOD_TEST], retries=0)
        self.assertEqual(result.status, "generated")
        self.assertEqual(result.usage.output_tokens, 40)
        self.assertEqual(result.usage.total_cost_usd, 0.5)
        validation = result.attempts[0].validation
        self.assertTrue(validation.passes_on_before and validation.fails_on_after and validation.fails_by_assertion)
        self.assertTrue(validation.names_flagged_element)
        self.assertTrue(Path(result.test_file).is_file())
        saved = json.loads((Path(result.test_file).parent / "result.json").read_text())
        self.assertEqual(saved["status"], "generated")

    def test_a_test_that_never_fails_is_invalid(self):
        result = self._generate([_NEVER_FAILS], retries=0)
        self.assertEqual(result.status, "invalid")
        self.assertFalse(result.attempts[0].validation.fails_on_after)

    def test_a_crashing_test_does_not_count_as_failing(self):
        result = self._generate([_CRASHES], retries=0)
        self.assertEqual(result.status, "invalid")
        self.assertTrue(result.attempts[0].validation.fails_on_after)
        self.assertFalse(result.attempts[0].validation.fails_by_assertion)

    def test_retry_fixes_an_invalid_test_and_sums_usage(self):
        result = self._generate([_NEVER_FAILS, _GOOD_TEST], retries=1)
        self.assertEqual(result.status, "generated")
        self.assertEqual(len(result.attempts), 2)
        self.assertEqual(result.usage.output_tokens, 80)

    def test_no_regression_means_no_test(self):
        report_file = self.case / _REPORT
        report = json.loads(report_file.read_text()) | {"is_regression": False, "regressions": []}
        report_file.write_text(json.dumps(report))
        result = self._generate([_GOOD_TEST])
        self.assertEqual(result.status, "skipped")
        self.assertIsNone(result.test_file)
        self.assertFalse((self.folder / "calls").exists())

    def test_skip_clears_files_from_an_earlier_regression_run(self):
        test_file = Path(self._generate([_GOOD_TEST], retries=0).test_file)
        report_file = self.case / _REPORT
        report = json.loads(report_file.read_text()) | {"is_regression": False, "regressions": []}
        report_file.write_text(json.dumps(report))
        self.assertEqual(self._generate([_GOOD_TEST]).status, "skipped")
        self.assertEqual([path.name for path in test_file.parent.iterdir()], ["result.json"])


if __name__ == "__main__":
    unittest.main()
