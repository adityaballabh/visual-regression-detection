"""Generate a unittest that compares a captured DOM snapshot to before."""

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

from image_diff.dom.parse import load_snapshot
from image_diff.model import Snapshot
from pipeline import diff_folder, reports_folder, tests_folder
from regression_detection.gemini_processor import DEFAULT_MODEL, REPORT_FORMATTER, RegressionReport
from test_generation.llm.generate import (
    Attempt,
    GenerationResult,
    flagged_boxes,
    load_report,
    portable_path,
    portable_text,
    validate_test,
)
from test_generation.scripted.snapshot_assertions import ElementTarget, StyleTarget

ReportTarget = tuple[int, ElementTarget, str]


def _report_targets(report_path: Path, boxes_path: Path) -> tuple[ReportTarget, ...]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("is_regression"), bool):
        raise TypeError(f"Regression report must contain a boolean 'is_regression': {report_path}")
    if not report["is_regression"]:
        return ()

    regressions = report.get("regressions")
    if not isinstance(regressions, list):
        raise TypeError("A regression report must contain a 'regressions' list")
    box_ids = [item.get("box_id") for item in regressions if isinstance(item, dict)]
    if len(box_ids) != len(regressions):
        raise ValueError("Each regression report entry must contain a box_id")
    if not box_ids:
        raise ValueError("The report has no target box ids in 'regressions'; cannot generate a focused snapshot test")
    if any(not isinstance(box_id, int) or isinstance(box_id, bool) for box_id in box_ids):
        raise TypeError("Report target box ids must be integers")

    boxes = json.loads(boxes_path.read_text(encoding="utf-8"))
    if not isinstance(boxes, list) or not all(isinstance(box, dict) for box in boxes):
        raise TypeError(f"Boxes file must contain a JSON array of box objects: {boxes_path}")
    boxes_by_id = {}
    for box in boxes:
        box_id = box.get("id")
        if not isinstance(box_id, int) or isinstance(box_id, bool):
            raise TypeError(f"Each box must have an integer id: {boxes_path}")
        if box_id in boxes_by_id:
            raise ValueError(f"Duplicate box id {box_id} in {boxes_path}")
        boxes_by_id[box_id] = box

    targets = []
    for box_id in dict.fromkeys(box_ids):
        if box_id not in boxes_by_id:
            raise ValueError(f"Report references box id {box_id}, which is missing from {boxes_path}")
        box = boxes_by_id[box_id]
        selector = box.get("selector")
        if not isinstance(selector, str) or not selector:
            raise ValueError(f"Target box {box_id} has no DOM selector in {boxes_path}; use DOM diff boxes.json")
        detail = box.get("detail", "")
        if not isinstance(detail, str):
            raise TypeError(f"Target box {box_id} has invalid change detail in {boxes_path}")
        frames = box.get("frames") or []
        if not isinstance(frames, list) or not all(isinstance(frame, str) for frame in frames):
            raise TypeError(f"Target box {box_id} has invalid frame selectors in {boxes_path}")
        targets.append((box_id, (tuple(frames), selector), detail))

    return tuple(targets)


def _reported_style_targets(
    targets: tuple[ReportTarget, ...],
    before: Snapshot,
    after: Snapshot,
) -> tuple[StyleTarget, ...]:
    before_by_key = {(element.frames, element.selector): element for element in before.elements}
    after_by_key = {(element.frames, element.selector): element for element in after.elements}
    styles_by_target: dict[ElementTarget, set[str]] = {}
    for box_id, target, detail in targets:
        before_element = before_by_key.get(target)
        after_element = after_by_key.get(target)
        if before_element is None or after_element is None:
            missing_side = "before" if before_element is None else "after"
            raise ValueError(f"Target box {box_id} element {target[1]} is missing from the {missing_side} snapshot")

        changed_styles = {
            name
            for name in set(before_element.styles) | set(after_element.styles)
            if before_element.styles.get(name) != after_element.styles.get(name)
            and name not in {"width", "height", "perspective-origin", "transform-origin"}
        }
        reported_styles = set()
        for change in detail.split(";"):
            name, separator, values = change.strip().partition(" ")
            if separator and " -> " in values and name in changed_styles:
                reported_styles.add(name)
        if not reported_styles and len(changed_styles) == 1:
            reported_styles = changed_styles
        if not reported_styles:
            if changed_styles:
                styles = ", ".join(sorted(changed_styles))
                raise ValueError(f"Target box {box_id} ({target[1]}) has ambiguous changed CSS styles ({styles})")
            raise ValueError(f"Target box {box_id} ({target[1]}) has no changed CSS style")
        styles_by_target.setdefault(target, set()).update(reported_styles)

    return tuple((target, tuple(sorted(styles))) for target, styles in sorted(styles_by_target.items()))


def _style_targets_literal(targets: tuple[StyleTarget, ...]) -> str:
    def tuple_line(values: tuple[str, ...], indentation: int) -> list[str]:
        contents = ", ".join(json.dumps(value) for value in values)
        one_line = f"({contents}{',' if len(values) == 1 else ''})"
        prefix = " " * indentation
        if len(prefix + one_line + ",") <= 120:
            return [f"{prefix}{one_line},"]
        return [
            f"{prefix}(",
            *(f"{prefix}    {json.dumps(value)}," for value in values),
            f"{prefix}),",
        ]

    lines = ["("]
    for (frames, selector), styles in targets:
        selector_literal = json.dumps(selector)
        target_line = f"        ({_string_tuple_literal(frames)}, {selector_literal}),"
        lines.append("    (")
        if len(target_line) <= 120:
            lines.append(target_line)
        else:
            lines.append("        (")
            lines.extend(tuple_line(frames, 12))
            lines.append(f"            {selector_literal},")
            lines.append("        ),")
        lines.extend(tuple_line(styles, 8))
        lines.append("    ),")
    lines.append(")")
    return "\n".join(lines)


def _string_tuple_literal(values: tuple[str, ...]) -> str:
    return f"({', '.join(json.dumps(value) for value in values)}{',' if len(values) == 1 else ''})"


def _relative_to_test(snapshot: Path, test_file: Path) -> str:
    return snapshot.resolve().relative_to(test_file.parent.resolve(), walk_up=True).as_posix()


def generate_test(
    before: Path,
    after: Path,
    report: Path,
    boxes: Path,
    output: Path,
    *,
    force: bool = False,
) -> Path | None:
    if not output.name.startswith("test_") or output.suffix != ".py":
        raise ValueError("Output filename must start with 'test_' and end with '.py'.")

    targets = _report_targets(report, boxes)
    # Skip since a test of the after state would lock in any regression detection missed
    if not targets:
        return None

    # Validate snapshots and ensure every report target has a report-relevant style change.
    before_snapshot = load_snapshot(before)
    after_snapshot = load_snapshot(after)
    style_targets = _reported_style_targets(targets, before_snapshot, after_snapshot)

    if output.exists() and not force:
        raise FileExistsError(f"Generated output already exists: {output}. Use --force to replace it.")

    output.parent.mkdir(parents=True, exist_ok=True)
    # Point at the case's captures instead of copying them next to the test
    expected_relative = json.dumps(_relative_to_test(before, output))
    actual_relative = json.dumps(_relative_to_test(after, output))
    style_targets_literal = _style_targets_literal(style_targets)
    output.write_text(
        f'''"""Generated DOM snapshot test; expected page state: before."""

import os
import unittest
from pathlib import Path

from test_generation.scripted.snapshot_assertions import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).parent / {expected_relative}
DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).parent / {actual_relative}
STYLE_TARGETS = {style_targets_literal}


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_before_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        actual_snapshot = Path(actual_path) if actual_path else DEFAULT_ACTUAL_SNAPSHOT
        assert_snapshot_matches(EXPECTED_SNAPSHOT, actual_snapshot, style_targets=STYLE_TARGETS)


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )
    return output


def _validate(
    case_folder: Path, detection_variant: str, report: RegressionReport, tests: Path
) -> tuple[str, str | None, Attempt]:
    flagged = flagged_boxes(case_folder, detection_variant, report)
    validation = validate_test(tests, case_folder.resolve(), flagged)
    attempt = Attempt(validation=validation)
    if validation.valid:
        return "generated", None, attempt
    return "invalid", "the test did not pass on the before snapshot and fail on the after snapshot", attempt


def _save_result(
    case_folder: Path,
    detection_model: str,
    detection_variant: str,
    detection_mode: str,
    tests: Path,
    test_file: Path | None,
    error: str | None = None,
) -> GenerationResult:
    report = load_report(case_folder, detection_model, detection_variant, detection_mode)
    attempts = []
    if error:
        status, reason = "error", error
    elif test_file is None:
        status, reason = "skipped", "the detection report found no regression"
    else:
        status, reason, attempt = _validate(case_folder, detection_variant, report, tests)
        attempts.append(attempt)
    # Same schema as the LLM generator so evaluation reads both alike
    result = GenerationResult(
        status=status,
        reason=reason,
        case=portable_path(case_folder.resolve()),
        detection_model=detection_model,
        detection_variant=detection_variant,
        detection_mode=detection_mode,
        flagged_box_ids=[regression.box_id for regression in report.regressions],
        test_file=portable_path(test_file.resolve()) if test_file else None,
        attempts=attempts,
        created_at=datetime.now(UTC).isoformat(timespec="seconds"),
    )
    tests.mkdir(parents=True, exist_ok=True)
    # Drop the LLM-only fields since a script has no CLI, code context or token usage
    llm_only = {"cli": True, "code": True, "usage": True, "attempts": {"__all__": {"usage", "session_id", "error"}}}
    (tests / "result.json").write_text(portable_text(REPORT_FORMATTER.serialize(result.model_dump(exclude=llm_only))))
    return result


def main():
    parser = argparse.ArgumentParser(
        description="Generate a focused unittest using the regression report and DOM boxes."
    )
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--detection-model", default=DEFAULT_MODEL)
    # The pixel-only diff has no selectors to assert on
    parser.add_argument("--detection-variant", choices=["all", "images", "boxes"], default="all")
    parser.add_argument("--detection-mode", choices=["context", "baseline"], default="context")
    parser.add_argument("--force", action="store_true", help="Replace generated files if they already exist")
    args = parser.parse_args()

    case_folder = args.case_folder
    reports = reports_folder(case_folder, args.detection_model, args.detection_variant)
    tests = tests_folder(
        case_folder, Path("scripted"), args.detection_model, args.detection_variant, args.detection_mode
    )
    output = None
    error = None
    try:
        output = generate_test(
            case_folder / "captures" / "before_snapshot.json",
            case_folder / "captures" / "after_snapshot.json",
            reports / f"report_{args.detection_mode}.json",
            diff_folder(case_folder, args.detection_variant) / "boxes.json",
            tests / "test_generated_regression.py",
            force=args.force,
        )
    # A missing or unreadable input means an earlier pipeline step did not run
    except (OSError, json.JSONDecodeError) as exception:
        parser.error(str(exception))
    # Record why no test could be built so evaluation still counts the case
    except (TypeError, ValueError) as exception:
        error = str(exception)
    result = _save_result(
        case_folder, args.detection_model, args.detection_variant, args.detection_mode, tests, output, error
    )
    print(f"{result.status}: {result.reason or result.test_file}")


if __name__ == "__main__":
    main()
