"""Generate a unittest that compares a captured DOM snapshot to before or after."""

import argparse
import json
import os
from pathlib import Path
from urllib.parse import urlsplit

from image_diff.dom.parse import load_snapshot
from image_diff.model import Snapshot
from image_diff.snapshot_test import ElementTarget, StyleTarget

ReportTarget = tuple[int, ElementTarget, str]


def _pr_identity(pr_url: str) -> tuple[str, str, int]:
    parsed = urlsplit(pr_url.strip())
    parts = parsed.path.strip("/").split("/")
    if (
        parsed.scheme not in ("http", "https")
        or parsed.hostname != "github.com"
        or len(parts) < 4
        or not parts[0]
        or not parts[1]
        or parts[2] != "pull"
        or not parts[3].isdigit()
    ):
        raise ValueError(f"Expected a GitHub pull request URL, got: {pr_url}")
    return parts[0].lower(), parts[1].removesuffix(".git").lower(), int(parts[3])


def _resolve_pr_inputs(pr_url: str, repository: Path) -> tuple[Path, Path, Path, Path]:
    repository = repository.expanduser().resolve()
    if not repository.is_dir():
        raise ValueError(f"Repository directory does not exist: {repository}")
    expected_pr = _pr_identity(pr_url)
    matching_cases = []
    ignored_directories = {".git", ".venv", "venv", "node_modules", "__pycache__", "out"}

    for current, directories, filenames in os.walk(repository):
        directories[:] = sorted(
            name for name in directories if name not in ignored_directories and not name.startswith(".")
        )
        if "pr.txt" not in filenames:
            continue
        pr_file = Path(current) / "pr.txt"
        try:
            if _pr_identity(pr_file.read_text(encoding="utf-8")) == expected_pr:
                matching_cases.append(Path(current))
        except ValueError:
            continue

    if not matching_cases:
        raise ValueError(f"No case in {repository} has a pr.txt matching {pr_url}")
    if len(matching_cases) > 1:
        cases = ", ".join(str(case) for case in sorted(matching_cases))
        raise ValueError(f"More than one case in {repository} matches {pr_url}: {cases}")

    case = matching_cases[0]
    before = case / "captures" / "before_snapshot.json"
    after = case / "captures" / "after_snapshot.json"
    boxes = case / "out" / "dom" / "boxes.json"
    missing = [path for path in (before, after, boxes) if not path.is_file()]
    if missing:
        paths = ", ".join(str(path) for path in missing)
        raise ValueError(f"The case matching {pr_url} is missing required snapshots or DOM boxes: {paths}")

    report_root = case / "out" / "regression_detection"
    reports = (
        [
            path
            for path in report_root.rglob("report_*.json")
            if path.is_file() and "no_snapshots" not in path.relative_to(report_root).parts
        ]
        if report_root.is_dir()
        else []
    )
    if not reports:
        raise ValueError(f"No DOM-compatible regression report found for {pr_url} under {report_root}")
    report = max(reports, key=lambda path: (path.stat().st_mtime_ns, path.as_posix()))
    return before, after, report, boxes


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

    expected_path = output.with_name(f"{output.stem}.expected.json")
    actual_path = output.with_name(f"{output.stem}.actual.json")
    generated_paths = {output.resolve(), expected_path.resolve(), actual_path.resolve()}
    input_paths = {before.resolve(), after.resolve(), report.resolve(), boxes.resolve()}
    if generated_paths & input_paths:
        raise ValueError("Generated test and expected snapshot must not overwrite any input file.")
    existing = [path for path in (output, expected_path, actual_path) if path.exists()]
    if existing and not force:
        files = ", ".join(map(str, existing))
        raise FileExistsError(f"Generated output already exists: {files}. Use --force to replace it.")

    output.parent.mkdir(parents=True, exist_ok=True)
    expected_snapshot = before if side == "before" else after
    expected_path.write_bytes(expected_snapshot.read_bytes())
    actual_path.write_bytes(after.read_bytes())
    expected_filename = json.dumps(expected_path.name)
    actual_filename = json.dumps(actual_path.name)
    style_targets_literal = _style_targets_literal(style_targets)
    output.write_text(
        f'''"""Generated DOM snapshot test; expected page state: {side}."""

import os
import unittest
from pathlib import Path

from image_diff.snapshot_test import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).with_name({expected_filename})
DEFAULT_ACTUAL_SNAPSHOT = Path(__file__).with_name({actual_filename})
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


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a focused unittest using the regression report and DOM boxes."
    )
    parser.add_argument("before", type=Path, nargs="?", help="Before DOM snapshot JSON")
    parser.add_argument("after", type=Path, nargs="?", help="After DOM snapshot JSON")
    parser.add_argument("--report", type=Path, help="Regression detection report JSON")
    parser.add_argument("--boxes", type=Path, help="DOM diff boxes.json used by the report")
    parser.add_argument("--pr", help="GitHub PR URL; look up its case in the visual-regression repository")
    parser.add_argument("--repo", type=Path, help="Path to the visual-regression repository used with --pr")
    parser.add_argument("--output", type=Path, required=True, help="Generated test filename (must start with test_)")
    parser.add_argument("--force", action="store_true", help="Replace generated files if they already exist")
    args = parser.parse_args()

    try:
        if args.pr:
            if args.repo is None:
                raise ValueError("--pr requires --repo")
            if any((args.before, args.after, args.report, args.boxes)):
                raise ValueError("Do not provide before, after, --report, or --boxes with --pr")
            before, after, report, boxes = _resolve_pr_inputs(args.pr, args.repo)
        else:
            if args.repo is not None:
                raise ValueError("--repo can only be used with --pr")
            if not all((args.before, args.after, args.report, args.boxes)):
                raise ValueError("Provide before, after, --report, and --boxes, or use --pr with --repo")
            before, after, report, boxes = args.before, args.after, args.report, args.boxes
        output = generate_test(before, after, report, boxes, args.output, force=args.force)
    except (OSError, TypeError, ValueError, json.JSONDecodeError) as error:
        parser.error(str(error))
    print(
        f"Generated {output}, {output.with_name(f'{output.stem}.expected.json')} "
        f"and {output.with_name(f'{output.stem}.actual.json')}"
    )


if __name__ == "__main__":
    main()
