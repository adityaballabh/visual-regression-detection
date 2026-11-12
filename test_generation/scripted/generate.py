"""Generate a unittest that compares a captured DOM snapshot to before or after."""

import argparse
import json
from pathlib import Path

from image_diff.dom.parse import load_snapshot
from image_diff.model import Snapshot
from pipeline import diff_folder, reports_folder, tests_folder
from regression_detection.gemini_processor import DEFAULT_MODEL
from test_generation.scripted.snapshot_assertions import ElementTarget, StyleTarget

ReportTarget = tuple[int, ElementTarget, str]


def _report_targets(report_path: Path, boxes_path: Path) -> tuple[str, tuple[ReportTarget, ...]]:
    report = json.loads(report_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict) or not isinstance(report.get("is_regression"), bool):
        raise TypeError(f"Regression report must contain a boolean 'is_regression': {report_path}")

    if report["is_regression"]:
        regressions = report.get("regressions")
        if not isinstance(regressions, list):
            raise TypeError("A regression report must contain a 'regressions' list")
        box_ids = [item.get("box_id") for item in regressions if isinstance(item, dict)]
        if len(box_ids) != len(regressions):
            raise ValueError("Each regression report entry must contain a box_id")
        side = "before"
    else:
        box_ids = report.get("intended_box_ids")
        if not isinstance(box_ids, list):
            raise TypeError("A non-regression report must contain an 'intended_box_ids' list")
        side = "after"

    if not box_ids:
        field = "regressions" if side == "before" else "intended_box_ids"
        raise ValueError(f"The report has no target box ids in '{field}'; cannot generate a focused snapshot test")
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

    return side, tuple(targets)


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
) -> Path:
    if not output.name.startswith("test_") or output.suffix != ".py":
        raise ValueError("Output filename must start with 'test_' and end with '.py'.")

    side, targets = _report_targets(report, boxes)

    # Validate snapshots and ensure every report target has a report-relevant style change.
    before_snapshot = load_snapshot(before)
    after_snapshot = load_snapshot(after)
    style_targets = _reported_style_targets(targets, before_snapshot, after_snapshot)

    if output.exists() and not force:
        raise FileExistsError(f"Generated output already exists: {output}. Use --force to replace it.")

    output.parent.mkdir(parents=True, exist_ok=True)
    expected_snapshot = before if side == "before" else after
    # Point at the case's captures instead of copying them next to the test
    expected_relative = json.dumps(_relative_to_test(expected_snapshot, output))
    actual_relative = json.dumps(_relative_to_test(after, output))
    style_targets_literal = _style_targets_literal(style_targets)
    output.write_text(
        f'''"""Generated DOM snapshot test; expected page state: {side}."""

import os
import unittest
from pathlib import Path

from test_generation.scripted.snapshot_assertions import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).parent / {expected_relative}
DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).parent / {actual_relative}
STYLE_TARGETS = {style_targets_literal}


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_{side}_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        actual_snapshot = Path(actual_path) if actual_path else DEFAULT_ACTUAL_SNAPSHOT
        assert_snapshot_matches(EXPECTED_SNAPSHOT, actual_snapshot, style_targets=STYLE_TARGETS)


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )
    return output


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
    tests = tests_folder(case_folder, Path("scripted"), args.detection_model, args.detection_variant)
    try:
        output = generate_test(
            case_folder / "captures" / "before_snapshot.json",
            case_folder / "captures" / "after_snapshot.json",
            reports / f"report_{args.detection_mode}.json",
            diff_folder(case_folder, args.detection_variant) / "boxes.json",
            tests / "test_generated_regression.py",
            force=args.force,
        )
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(f"Generated {output}")


if __name__ == "__main__":
    main()
