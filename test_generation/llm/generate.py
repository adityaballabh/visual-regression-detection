"""Generate a failing test for a detected regression with a CLI agent (Claude Code).

Runs after regression detection. Reads the detection report of a case and, if it found a regression, asks Claude Code
to write a repo-agnostic `unittest` that checks a captured DOM snapshot: it passes on the before snapshot and fails on
the after snapshot, on the elements the detector flagged. The agent also gets the code behind the change (the
PrairieLearn PR checkout or the case's HTML) so it can inspect it, run the test and pick sturdy assertions.

The script then checks the test itself against both snapshots, and writes the test and a `result.json` (validity,
token usage and cost) to `<case_folder>/out/test_generation/llm/<cli model>/detection-<detection model>/<detection variant>/<detection mode>/`.

Usage, from the repository root:
    python -m test_generation.llm.generate CASE_FOLDER [--detection-model MODEL]
        [--detection-variant all|images|boxes|no_snapshots] [--detection-mode context|baseline]
        [--cli-model claude-sonnet-5-5] [--max-budget-usd 2.0] [--retries 1] [--cache-dir DIR] [--run-detection] [--dry-run]

`--run-detection` first runs the earlier pipeline steps (capture, image diff, regression detection) on the case.
`--dry-run` prints the prompt and the Claude Code command without running the agent.
"""

import argparse
import difflib
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from pydantic import BaseModel

from image_diff.dom.parse import load_snapshot
from pipeline import _pr_repo, detect_regressions, diff_folder, prepare_case, reports_folder, tests_folder
from regression_detection.gemini_processor import (
    DEFAULT_MODEL,
    REPO_ROOT,
    REPORT_FORMATTER,
    VARIANTS,
    RegressionReport,
)

DEFAULT_CLI_MODEL = "claude-sonnet-5-5"
DEFAULT_MAX_BUDGET_USD = 2.0
DEFAULT_CACHE_DIR = Path.home() / ".cache" / "visual-regression-detection"
TEST_MODULE = "test_generated_regression"
TEST_FILE = f"{TEST_MODULE}.py"
AGENT_TIMEOUT_SECONDS = 30 * 60
TEST_TIMEOUT_SECONDS = 120
# The PR's own capture artifacts are huge and say nothing about the code
_PR_ARTIFACTS = ".github/pr-images/"


# ---------------------------------------------------------------- result schema


class Usage(BaseModel):
    input_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0
    output_tokens: int = 0
    total_cost_usd: float = 0.0
    num_turns: int = 0
    duration_ms: int = 0

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(**{name: getattr(self, name) + getattr(other, name) for name in type(self).model_fields})


class Validation(BaseModel):
    passes_on_before: bool
    fails_on_after: bool
    # The failure is an assertion, not an import error or a crash in the test
    fails_by_assertion: bool
    # The failure message names a flagged element, None when no flagged box has a selector
    names_flagged_element: bool | None
    before_output: str
    after_output: str

    @property
    def valid(self) -> bool:
        return self.passes_on_before and self.fails_on_after and self.fails_by_assertion


class Attempt(BaseModel):
    usage: Usage = Usage()
    session_id: str | None = None
    error: str | None = None
    validation: Validation | None = None


class CodeContext(BaseModel):
    kind: Literal["pull_request", "html", "none"]
    pr_url: str | None = None
    head_sha: str | None = None
    code_dir: str | None = None
    diff_file: str | None = None


class GenerationResult(BaseModel):
    status: Literal["generated", "skipped", "invalid", "error"]
    reason: str | None = None
    case: str
    detection_model: str
    detection_variant: str
    detection_mode: str
    flagged_box_ids: list[int]
    cli: dict[str, str] | None = None
    code: CodeContext | None = None
    test_file: str | None = None
    attempts: list[Attempt] = []
    usage: Usage = Usage()
    created_at: str


# ------------------------------------------------------------------ report input


def load_report(case_folder: Path, model: str, variant: str, mode: str) -> RegressionReport:
    report_file = reports_folder(case_folder, model, variant) / f"report_{mode}.json"
    if not report_file.is_file():
        raise SystemExit(f"{report_file} not found, run regression detection first (or pass --run-detection)")
    return RegressionReport.model_validate_json(report_file.read_text())


def flagged_boxes(case_folder: Path, variant: str, report: RegressionReport) -> list[dict]:
    """The report's regressions joined with their boxes, keeping the selectors for the agent."""
    boxes = {box["id"]: box for box in json.loads((diff_folder(case_folder, variant) / "boxes.json").read_text())}
    flagged = []
    for regression in report.regressions:
        box = boxes[regression.box_id]
        flagged.append(
            {key: value for key, value in box.items() if value is not None}
            | {
                "category": regression.category,
                "severity": regression.severity,
                "explanation": regression.explanation,
                "violated_rule": regression.violated_rule,
            }
        )
    return flagged


# -------------------------------------------------------------- the code to inspect


def _git(*args: str, cwd: Path) -> str:
    return subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True, text=True).stdout.strip()


def _pull_request_context(pr_url: str, out_folder: Path, cache_dir: Path, fetch: bool) -> CodeContext:
    """The PR's head checked out once in the cache, plus the PR's diff as a file next to the test."""
    repo, number = _pr_repo(pr_url)
    pull = repo.get_pull(number)
    name = repo.full_name.replace("/", "__")
    context = CodeContext(kind="pull_request", pr_url=pr_url, head_sha=pull.head.sha)
    if not fetch:
        return context

    git_dir = cache_dir / "repos" / name
    if not (git_dir / ".git").is_dir():
        git_dir.mkdir(parents=True, exist_ok=True)
        _git("init", "--quiet", cwd=git_dir)
        _git("remote", "add", "origin", repo.clone_url, cwd=git_dir)
    # A shallow fetch of the PR head only, since the history of a big repo isn't needed
    print(f"fetching {repo.full_name} PR {number} (cached in {cache_dir})", flush=True)
    _git("fetch", "--quiet", "--depth", "1", "origin", f"refs/pull/{number}/head", cwd=git_dir)
    head_sha = _git("rev-parse", "FETCH_HEAD", cwd=git_dir)
    checkout = cache_dir / "checkouts" / f"{name}-pr{number}-{head_sha[:8]}"
    if not checkout.is_dir():
        _git("worktree", "add", "--quiet", "--detach", str(checkout), head_sha, cwd=git_dir)

    diff = []
    for changed in pull.get_files():
        if changed.filename.startswith(_PR_ARTIFACTS) or not changed.patch:
            continue
        before_name = changed.previous_filename or changed.filename
        diff.append(f"diff --git a/{before_name} b/{changed.filename}\n{changed.patch}\n")
    diff_file = out_folder / "code_changes.diff"
    diff_file.write_text("".join(diff))
    return context.model_copy(update={"head_sha": head_sha, "code_dir": str(checkout), "diff_file": str(diff_file)})


def _html_context(case_folder: Path, out_folder: Path, write: bool) -> CodeContext:
    before, after = case_folder / "html" / "before.html", case_folder / "html" / "after.html"
    diff = difflib.unified_diff(
        before.read_text().splitlines(keepends=True),
        after.read_text().splitlines(keepends=True),
        fromfile="before.html",
        tofile="after.html",
    )
    diff_file = out_folder / "code_changes.diff"
    if write:
        diff_file.write_text("".join(diff))
    return CodeContext(kind="html", code_dir=str(case_folder / "html"), diff_file=str(diff_file))


def _code_context(case_folder: Path, out_folder: Path, cache_dir: Path, fetch: bool) -> CodeContext:
    pr_file = case_folder / "pr.txt"
    if pr_file.is_file():
        return _pull_request_context(pr_file.read_text().strip(), out_folder, cache_dir, fetch)
    if (case_folder / "html" / "before.html").is_file() and (case_folder / "html" / "after.html").is_file():
        return _html_context(case_folder, out_folder, write=fetch)
    return CodeContext(kind="none")


def portable_path(path: Path) -> str:
    if path.is_relative_to(REPO_ROOT):
        return str(path.relative_to(REPO_ROOT))
    # Leave the username out of paths like the cached PR checkout
    if path.is_relative_to(Path.home()):
        return str("~" / path.relative_to(Path.home()))
    return str(path)


def portable_text(text: str) -> str:
    # Same rules as portable_path, for paths inside saved prompts and outputs
    text = text.replace(f"{REPO_ROOT}/", "").replace(str(REPO_ROOT), ".")
    return text.replace(f"{Path.home()}/", "~/")


def _portable_code(code: CodeContext) -> CodeContext:
    paths = {}
    for name in ("code_dir", "diff_file"):
        path = getattr(code, name)
        if path:
            paths[name] = portable_path(Path(path))
    return code.model_copy(update=paths)


def _snapshot_facts(case_folder: Path, flagged: list[dict]) -> list[dict]:
    """What the two snapshots say about each flagged element, so the agent starts from real values."""
    captures = case_folder / "captures"
    snapshots = [load_snapshot(captures / "before_snapshot.json"), load_snapshot(captures / "after_snapshot.json")]
    indexes = [{(element.frames, element.selector): element for element in snapshot.elements} for snapshot in snapshots]
    facts = []
    for box in flagged:
        if not box.get("selector"):
            continue
        key = (tuple(box.get("frames", [])), box["selector"])
        before, after = indexes[0].get(key), indexes[1].get(key)
        fact: dict = {"selector": box["selector"], "in_before": before is not None, "in_after": after is not None}
        present = before or after
        if present:
            fact["tag"] = present.tag
            fact["own_text"] = present.own_text
        for side, element in (("before", before), ("after", after)):
            if element:
                fact[f"box_{side}"] = {
                    "x1": element.box.x1,
                    "y1": element.box.y1,
                    "x2": element.box.x2,
                    "y2": element.box.y2,
                }
        if before and after:
            fact["styles_that_differ"] = {
                name: {"before": before.styles.get(name), "after": after.styles.get(name)}
                for name in sorted(set(before.styles) | set(after.styles))
                if before.styles.get(name) != after.styles.get(name)
            }
            if before.attributes != after.attributes:
                fact["attributes"] = {"before": before.attributes, "after": after.attributes}
        facts.append(fact)
    return facts


# ------------------------------------------------------------------------ prompt

PROMPT = """\
A visual regression detector found that a code change broke a page. Write ONE Python `unittest` that pins down the
correct page: it must PASS on the DOM snapshot of the page before the change and FAIL on the snapshot after it. The
test will later be run against a snapshot captured from any build of the app, so it must not depend on this repository
or its code, only on the snapshot.

## Detected regression
{summary}

Flagged boxes. `selector` and `frames` locate the element in the snapshots, `before` and `after` are pixel boxes in the
screenshots, `detail` is the DOM change behind the box when known:
{flagged}

What the two snapshots say about those elements (values come straight from the snapshots):
{facts}

## Design intent of the change
{design_intent}

## Design language
{design_language}

## Files
- Before snapshot (the correct page): {before_snapshot}
- After snapshot (the regressed page): {after_snapshot}
- Code behind the change: {code}
- Changes between before and after: {diff}

Inspect the code and the diff to understand which component renders the flagged elements and what change broke
them. The diff may include unrelated changes (tests, capture helpers), ignore those. The snapshot format is defined
by `image_diff/model.py` and `image_diff/dom/parse.py` in {repo_root}.

## Snapshot API
`from image_diff.dom.parse import load_snapshot` gives `load_snapshot(Path) -> Snapshot`, with `snapshot.elements`
in document order. Each `Element` has:
- `selector`: positional CSS selector, unique within its frame, and `frames`: the selectors of the enclosing iframes
- `tag`, `attributes` (dict), `own_text`, `parent` and `id`
- `box`: page pixels with `x1`, `y1`, `x2`, `y2`, `width`, `height`
- `styles`: computed CSS, property name to value string, like `"background-color": "rgb(220, 252, 231)"`
- `visible`, `paint_order`, `text_box`

## The test
Write exactly one file, {test_path}, and nothing else. It must:
1. Read the snapshot under test from the `ACTUAL_SNAPSHOT` environment variable, like this skeleton:

```python
import os
import unittest
from pathlib import Path

from image_diff.dom.parse import load_snapshot


class GeneratedRegressionTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        path = os.environ.get("ACTUAL_SNAPSHOT")
        if not path:
            raise AssertionError("Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        cls.snapshot = load_snapshot(Path(path))
```

2. Find each flagged element by `frames` and `selector`. If a box has no selector, find the element by its text, tag
   and position from the snapshots. Prefer a more stable id, class or `data-` attribute found in the code only if it
   is present in both snapshots.
3. Assert on the property that is wrong: computed styles, size or position, text, attributes, or presence. Take every
   expected value from the BEFORE snapshot, never guess one. Sizes and positions may differ by 1 px.
4. Assert only on what was flagged. Do not compare the whole page, and do not assert on changes the design intent
   says are intended, since those differ between before and after by design.
5. Fail with a message naming the selector, the property, the expected and the actual value.
6. Use only the standard library and `image_diff`, no absolute paths, no network.
7. Put a docstring on the test saying which regression it guards and which code change caused it.

## Verify before you finish
Run both commands from your working directory, each one on its own, exactly as written: no `cd`, no chaining and no
pipes. The first must pass and the second must fail with an assertion about a flagged element, not an import error or
a crash. Fix the test until both hold.
```
{before_command}
{after_command}
```
Finish with one or two sentences on what the test asserts."""

_RETRY_NOTE = """

## Previous attempt
Your last test did not meet the requirements, so it was removed. Here is what happened when it was checked:
- On the before snapshot it {before_result}.
- On the after snapshot it {after_result}.

Output on the before snapshot:
{before_output}

Output on the after snapshot:
{after_output}

The test you wrote:
{test_source}

Write a corrected test."""


def _test_command(snapshot: Path) -> str:
    env = f"ACTUAL_SNAPSHOT={shlex.quote(str(snapshot))} PYTHONPATH={shlex.quote(str(REPO_ROOT))}"
    return f"{env} {shlex.quote(sys.executable)} -m unittest {TEST_MODULE}"


def _build_prompt(
    report: RegressionReport,
    flagged: list[dict],
    case_folder: Path,
    out_folder: Path,
    code: CodeContext,
    facts: list[dict],
) -> str:
    design = case_folder / "design"

    def read(name: str) -> str:
        file = design / name
        return file.read_text().strip() if file.is_file() else "(not provided)"

    code_text = {
        "pull_request": f"{code.code_dir} (checkout of the PR head, {code.pr_url})",
        "html": f"{code.code_dir} (before.html and after.html, the whole page)",
        "none": "(not available)",
    }[code.kind]
    return PROMPT.format(
        summary=report.summary,
        flagged=json.dumps(flagged, indent=1),
        facts=json.dumps(facts, indent=1),
        design_intent=read("design_intent.md"),
        design_language=read("design_language.md"),
        before_snapshot=case_folder / "captures" / "before_snapshot.json",
        after_snapshot=case_folder / "captures" / "after_snapshot.json",
        code=code_text,
        diff=code.diff_file or "(not available)",
        repo_root=REPO_ROOT,
        test_path=out_folder / TEST_FILE,
        before_command=_test_command(case_folder / "captures" / "before_snapshot.json"),
        after_command=_test_command(case_folder / "captures" / "after_snapshot.json"),
    )


def _retry_prompt(prompt: str, validation: Validation, test_file: Path) -> str:
    before_result = "passed, as it should" if validation.passes_on_before else "failed, but it must pass"
    if not validation.fails_on_after:
        after_result = "passed, but it must fail"
    elif not validation.fails_by_assertion:
        after_result = "crashed with an error in the test itself, it must fail by an assertion"
    else:
        after_result = "failed by an assertion, as it should"
    return prompt + _RETRY_NOTE.format(
        before_result=before_result,
        after_result=after_result,
        before_output=validation.before_output[-3000:],
        after_output=validation.after_output[-3000:],
        test_source=test_file.read_text() if test_file.is_file() else "(no file was written)",
    )


# ------------------------------------------------------------------------- agent


def _agent_command(
    claude_bin: str, model: str, max_budget_usd: float, case_folder: Path, out_folder: Path, code: CodeContext
) -> list[str]:
    # The agent reads the case, the snapshot code and the app's code, and may only write the test file
    case_dirs = [str(REPO_ROOT / "image_diff"), str(case_folder)]
    if code.code_dir:
        case_dirs.append(code.code_dir)
    allowed = [
        "Read",
        "Grep",
        "Glob",
        # A rule path starting with // is absolute, and Edit covers every tool that writes a file
        f"Edit(/{out_folder / TEST_FILE})",
        f"Write(/{out_folder / TEST_FILE})",
        "Bash(git diff:*)",
        "Bash(git log:*)",
        "Bash(git show:*)",
        f"Bash(ACTUAL_SNAPSHOT=* PYTHONPATH=* {sys.executable} -m unittest {TEST_MODULE})",
    ]
    command = [
        claude_bin,
        "-p",
        "--output-format",
        "json",
        "--model",
        model,
        "--max-budget-usd",
        str(max_budget_usd),
        "--permission-mode",
        "dontAsk",
        "--no-session-persistence",
        "--allowedTools",
        ",".join(allowed),
    ]
    for directory in case_dirs:
        command += ["--add-dir", directory]
    return command


def _usage_from(output: dict) -> Usage:
    usage = output.get("usage", {})
    return Usage(
        input_tokens=usage.get("input_tokens", 0),
        cache_creation_input_tokens=usage.get("cache_creation_input_tokens", 0),
        cache_read_input_tokens=usage.get("cache_read_input_tokens", 0),
        output_tokens=usage.get("output_tokens", 0),
        total_cost_usd=output.get("total_cost_usd", 0.0),
        num_turns=output.get("num_turns", 0),
        duration_ms=output.get("duration_ms", 0),
    )


def _run_agent(prompt: str, command: list[str], out_folder: Path, attempt: int) -> Attempt:
    """Run Claude Code headless and read the token usage and cost from its JSON result."""
    try:
        done = subprocess.run(
            command,
            cwd=out_folder,
            input=prompt,
            capture_output=True,
            text=True,
            check=False,
            timeout=AGENT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return Attempt(usage=Usage(), error=f"agent timed out after {AGENT_TIMEOUT_SECONDS}s")
    attempts_folder = out_folder / "attempts"
    attempts_folder.mkdir(exist_ok=True)
    attempt_file = attempts_folder / f"{attempt}.json"
    try:
        output = json.loads(done.stdout)
    except json.JSONDecodeError:
        # Keep the raw output since it is not JSON when the agent crashes
        attempt_file.write_text(portable_text(done.stdout))
        return Attempt(usage=Usage(), error=f"agent exited {done.returncode}: {(done.stderr or done.stdout)[-500:]}")
    attempt_file.write_text(portable_text(REPORT_FORMATTER.serialize(output)))
    error = None
    if done.returncode != 0 or output.get("is_error"):
        error = f"{output.get('subtype', 'error')}: {str(output.get('result', ''))[-500:]}"
    return Attempt(usage=_usage_from(output), session_id=output.get("session_id"), error=error)


# -------------------------------------------------------------------- validation


def _run_test(out_folder: Path, snapshot: Path) -> tuple[int, str]:
    env = {**os.environ, "ACTUAL_SNAPSHOT": str(snapshot), "PYTHONPATH": str(REPO_ROOT)}
    try:
        done = subprocess.run(
            [sys.executable, "-m", "unittest", TEST_MODULE],
            cwd=out_folder,
            env=env,
            capture_output=True,
            text=True,
            check=False,
            timeout=TEST_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired:
        return 1, f"timed out after {TEST_TIMEOUT_SECONDS}s"
    return done.returncode, done.stdout + done.stderr


def _names_flagged_element(output: str, flagged: list[dict]) -> bool | None:
    selectors = [box["selector"] for box in flagged if box.get("selector")]
    if not selectors:
        return None
    # The last steps are enough, a test may print a shortened selector
    return any(" > ".join(selector.split(" > ")[-2:]) in output for selector in selectors)


def _format_test(test_file: Path) -> None:
    """Format the test like the repo, since CI checks every file with `ruff format`. Skipped when ruff is missing."""
    for command in (["ruff"], [sys.executable, "-m", "ruff"]):
        try:
            done = subprocess.run(
                [*command, "format", "--config", str(REPO_ROOT / "ruff.toml"), str(test_file)],
                capture_output=True,
                stdin=subprocess.DEVNULL,
                check=False,
            )
        except OSError:
            continue
        if done.returncode == 0:
            return
    print("ruff not found, the generated test is not formatted", flush=True)


def validate_test(out_folder: Path, case_folder: Path, flagged: list[dict]) -> Validation:
    """Check the written test the way it will be used: pass on the before snapshot, fail on the after one."""
    before_code, before_output = _run_test(out_folder, case_folder / "captures" / "before_snapshot.json")
    after_code, after_output = _run_test(out_folder, case_folder / "captures" / "after_snapshot.json")
    # unittest prints `FAILED (failures=N)` for assertions and adds `errors=N` for crashes and import errors
    assertion_only = re.search(r"FAILED \(failures=\d+\)", after_output) is not None
    return Validation(
        passes_on_before=before_code == 0,
        fails_on_after=after_code != 0,
        fails_by_assertion=assertion_only,
        names_flagged_element=_names_flagged_element(after_output, flagged) if after_code != 0 else None,
        before_output=before_output,
        after_output=after_output,
    )


# ---------------------------------------------------------------------- the flow


def _claude_version(claude_bin: str) -> str:
    try:
        return subprocess.run(
            [claude_bin, "--version"], capture_output=True, text=True, stdin=subprocess.DEVNULL, check=False
        ).stdout.strip()
    except OSError:
        return "unknown"


def generate_test(
    case_folder: Path,
    *,
    detection_model: str = DEFAULT_MODEL,
    detection_variant: str = "all",
    detection_mode: str = "context",
    cli_model: str = DEFAULT_CLI_MODEL,
    claude_bin: str = "claude",
    max_budget_usd: float = DEFAULT_MAX_BUDGET_USD,
    retries: int = 1,
    cache_dir: Path = DEFAULT_CACHE_DIR,
    dry_run: bool = False,
) -> GenerationResult | None:
    # The agent runs in the output folder, so every path it is given has to be absolute
    case_folder = case_folder.resolve()
    report = load_report(case_folder, detection_model, detection_variant, detection_mode)
    out_folder = tests_folder(case_folder, Path("llm", cli_model), detection_model, detection_variant, detection_mode)

    def result(status: str, **fields) -> GenerationResult:
        base = {
            "status": status,
            "case": portable_path(case_folder),
            "detection_model": detection_model,
            "detection_variant": detection_variant,
            "detection_mode": detection_mode,
            "flagged_box_ids": [regression.box_id for regression in report.regressions],
            "cli": {"name": "claude-code", "version": _claude_version(claude_bin), "model": cli_model},
            "code": CodeContext(kind="none"),
            "created_at": datetime.now(UTC).isoformat(timespec="seconds"),
        }
        return GenerationResult(**(base | fields))

    def save(outcome: GenerationResult) -> GenerationResult:
        out_folder.mkdir(parents=True, exist_ok=True)
        (out_folder / "result.json").write_text(portable_text(REPORT_FORMATTER.serialize(outcome.model_dump())))
        return outcome

    if not report.is_regression:
        # No regression, no test, so clear files from an earlier run that found one
        shutil.rmtree(out_folder, ignore_errors=True)
        return save(result("skipped", reason="the detection report found no regression"))

    flagged = flagged_boxes(case_folder, detection_variant, report)
    if not dry_run:
        out_folder.mkdir(parents=True, exist_ok=True)
    code = _code_context(case_folder, out_folder, cache_dir, fetch=not dry_run)
    prompt = _build_prompt(report, flagged, case_folder, out_folder, code, _snapshot_facts(case_folder, flagged))
    command = _agent_command(claude_bin, cli_model, max_budget_usd, case_folder, out_folder, code)
    if dry_run:
        print(prompt)
        print(f"\n--- command (prompt on stdin, cwd {out_folder}) ---\n{shlex.join(command)}")
        return None
    if shutil.which(claude_bin) is None:
        raise SystemExit(f"{claude_bin} not found, install Claude Code or pass --claude-bin")

    (out_folder / "prompt.md").write_text(portable_text(prompt))
    test_file = out_folder / TEST_FILE
    test_file.unlink(missing_ok=True)
    attempts: list[Attempt] = []
    total = Usage()
    current_prompt = prompt
    for number in range(1, retries + 2):
        print(f"attempt {number}: running {cli_model} on the case", flush=True)
        attempt = _run_agent(current_prompt, command, out_folder, number)
        total += attempt.usage
        attempts.append(attempt)
        if attempt.error:
            print(f"attempt {number}: agent error: {attempt.error}", flush=True)
            break
        if not test_file.is_file():
            attempt.error = "the agent did not write the test file"
            break
        _format_test(test_file)
        attempt.validation = validate_test(out_folder, case_folder, flagged)
        print(f"attempt {number}: valid={attempt.validation.valid}", flush=True)
        if attempt.validation.valid:
            break
        current_prompt = _retry_prompt(prompt, attempt.validation, test_file)
        if number <= retries:
            test_file.unlink(missing_ok=True)

    final = attempts[-1]
    if final.validation and final.validation.valid:
        status, reason = "generated", None
    elif final.error:
        status, reason = "error", final.error
    else:
        status, reason = "invalid", "the test did not pass on the before snapshot and fail on the after snapshot"
    return save(
        result(
            status,
            reason=reason,
            code=_portable_code(code),
            test_file=portable_path(test_file) if test_file.is_file() else None,
            attempts=attempts,
            usage=total,
        )
    )


def main():
    parser = argparse.ArgumentParser(prog="test_generation.llm.generate", description=__doc__.split("\n\n")[0])
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--detection-model", default=DEFAULT_MODEL)
    parser.add_argument("--detection-variant", choices=VARIANTS, default="all")
    parser.add_argument("--detection-mode", choices=["context", "baseline"], default="context")
    parser.add_argument("--cli-model", default=DEFAULT_CLI_MODEL, help="Claude Code model or alias")
    parser.add_argument("--claude-bin", default="claude")
    parser.add_argument("--max-budget-usd", type=float, default=DEFAULT_MAX_BUDGET_USD, help="limit for one attempt")
    parser.add_argument("--retries", type=int, default=1, help="extra attempts when the test is not valid")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR)
    parser.add_argument("--run-detection", action="store_true", help="run capture, image diff and detection first")
    parser.add_argument("--dry-run", action="store_true", help="print the prompt and command, don't run the agent")
    args = parser.parse_args()

    if args.run_detection:
        prepare_case(args.case_folder)
        reports = detect_regressions(
            args.case_folder, args.detection_variant, args.detection_model, args.detection_mode, args.dry_run
        )
        for mode, report in reports.items():
            flagged = ", ".join(str(regression.box_id) for regression in report.regressions)
            print(f"detection {mode}: {f'regression in boxes {flagged}' if report.is_regression else 'no regression'}")
    outcome = generate_test(
        args.case_folder,
        detection_model=args.detection_model,
        detection_variant=args.detection_variant,
        detection_mode=args.detection_mode,
        cli_model=args.cli_model,
        claude_bin=args.claude_bin,
        max_budget_usd=args.max_budget_usd,
        retries=args.retries,
        cache_dir=args.cache_dir,
        dry_run=args.dry_run,
    )
    if outcome is None:
        return
    print(f"{outcome.status}: {outcome.reason or outcome.test_file}")
    print(
        f"tokens in/out {outcome.usage.input_tokens}/{outcome.usage.output_tokens}, ${outcome.usage.total_cost_usd:.3f}"
    )
    sys.exit(0 if outcome.status in ("generated", "skipped") else 1)


if __name__ == "__main__":
    main()
