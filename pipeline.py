import argparse
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath

from cases import diff_folder, pr_repo, reports_folder
from image_diff.capture import capture_html_pair
from image_diff.diff import diff_files
from image_diff.model import Side
from regression_detection.gemini_processor import DEFAULT_MODEL, VARIANTS, Case, RegressionReport, load_env, run_case
from test_generation.llm.generate import DEFAULT_CLI_MODEL, GenerationResult
from test_generation.llm.generate import generate_test as generate_llm_test
from test_generation.scripted.generate import generate_case_test as generate_scripted_test

_CAPTURE_NAMES = ("before.png", "before_snapshot.json", "after.png", "after_snapshot.json")
# Hardcoded to where the PrairieLearn fork stores its design language
_REPO_DESIGN_LANGUAGE_PATH = "docs/design-standards.md"


def _has_captures(folder: Path) -> bool:
    return all((folder / name).is_file() for name in _CAPTURE_NAMES)


def _has_html_pair(folder: Path) -> bool:
    return all((folder / f"{side}.html").is_file() for side in Side)


def _download_pr_captures(pr_url: str, captures_folder: Path):
    repo, number = pr_repo(pr_url)
    pull = repo.get_pull(number)

    # Group the capture files by their folder under .github/pr-images/
    raw_urls_by_capture = defaultdict(dict)
    for pr_file in pull.get_files():
        path = PurePosixPath(pr_file.filename)
        if path.parts[:2] == (".github", "pr-images"):
            raw_urls_by_capture[path.parent.name][path.name] = pr_file.raw_url

    # Fail if the PR has more than one capture
    if len(raw_urls_by_capture) > 1:
        raise SystemExit(f"{pr_url} has captures for several components: {', '.join(sorted(raw_urls_by_capture))}")
    raw_urls = next(iter(raw_urls_by_capture.values()), {})

    captures_folder.mkdir(parents=True, exist_ok=True)
    for name in _CAPTURE_NAMES:
        if name not in raw_urls:
            raise SystemExit(f"{pr_url} has no {name} under .github/pr-images/")
        urllib.request.urlretrieve(raw_urls[name], captures_folder / name)


def _download_design_language(pr_url: str, design_language: Path):
    repo, _ = pr_repo(pr_url)
    content = repo.get_contents(_REPO_DESIGN_LANGUAGE_PATH).decoded_content
    design_language.parent.mkdir(parents=True, exist_ok=True)
    design_language.write_bytes(content)


def _download_design_intent(pr_url: str, design_intent: Path):
    repo, number = pr_repo(pr_url)
    description = repo.get_pull(number).body

    # The capture script writes the intent under Description, before the screenshots
    intent = description.partition("## Screenshots")[0].removeprefix("# Description").strip()
    design_intent.parent.mkdir(parents=True, exist_ok=True)
    design_intent.write_text(intent)


def _diff(captures_folder: Path, out_folder: Path):
    before_path, after_path = captures_folder / "before.png", captures_folder / "after.png"
    snapshot_paths = captures_folder / "before_snapshot.json", captures_folder / "after_snapshot.json"
    diff_files(before_path, after_path, out_folder / "dom", snapshot_paths)
    diff_files(before_path, after_path, out_folder / "pixel")


def prepare_case(case_folder: Path):
    captures_folder = case_folder / "captures"
    html_folder = case_folder / "html"
    pr_file = case_folder / "pr.txt"
    # Use existing captures, otherwise capture them from html or download them from a PrairieLearn PR
    if not _has_captures(captures_folder):
        if _has_html_pair(html_folder):
            capture_html_pair(html_folder, captures_folder)
        elif pr_file.is_file():
            _download_pr_captures(pr_file.read_text().strip(), captures_folder)
        else:
            raise SystemExit(f"{case_folder} needs captures/, html/ or pr.txt")

    design_language = case_folder / "design" / "design_language.md"
    design_intent = case_folder / "design" / "design_intent.md"
    # Fetch the repo's design language and the PR's intent for a PR case without its own
    if pr_file.is_file() and not design_language.is_file():
        _download_design_language(pr_file.read_text().strip(), design_language)
    if pr_file.is_file() and not design_intent.is_file():
        _download_design_intent(pr_file.read_text().strip(), design_intent)

    _diff(captures_folder, case_folder / "out")


def detect_regressions(
    case_folder: Path,
    detection_variant: str,
    detection_model: str,
    detection_mode: str,
    detection_dry_run: bool,
) -> dict[str, RegressionReport]:
    load_env()
    case = Case(diff_folder(case_folder, detection_variant), case_folder / "design", detection_variant)
    out = reports_folder(case_folder, detection_model, detection_variant)
    return run_case(case, detection_mode, detection_model, out, detection_dry_run)


def generate_test(
    case_folder: Path,
    detection_model: str,
    detection_variant: str,
    detection_mode: str,
    test_generator: str,
    cli_model: str,
) -> GenerationResult:
    if test_generator == "scripted":
        # Replace the test from an earlier run since detection just ran again
        return generate_scripted_test(case_folder, detection_model, detection_variant, detection_mode, force=True)
    return generate_llm_test(
        case_folder,
        detection_model=detection_model,
        detection_variant=detection_variant,
        detection_mode=detection_mode,
        cli_model=cli_model,
    )


def _verdict(report: RegressionReport) -> str:
    if not report.is_regression:
        return "no regression"
    box_ids = ", ".join(str(regression.box_id) for regression in report.regressions)
    return f"regression in boxes {box_ids}"


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--detection-variant", choices=VARIANTS, default="all")
    parser.add_argument("--detection-model", default=DEFAULT_MODEL)
    parser.add_argument("--detection-mode", choices=["context", "baseline", "both"], default="context")
    parser.add_argument("--detection-dry-run", action="store_true")
    parser.add_argument("--test-generator", choices=["scripted", "llm"], default="llm")
    parser.add_argument("--cli-model", default=DEFAULT_CLI_MODEL, help="Claude Code model for the llm generator")
    args = parser.parse_args()
    # The scripted generator needs selectors, which pixel boxes do not have
    if args.test_generator == "scripted" and args.detection_variant == "no_snapshots":
        parser.error("the scripted test generator does not support the no_snapshots variant")

    prepare_case(args.case_folder)
    reports = detect_regressions(
        args.case_folder,
        args.detection_variant,
        args.detection_model,
        args.detection_mode,
        args.detection_dry_run,
    )
    out = reports_folder(args.case_folder, args.detection_model, args.detection_variant)
    for mode, report in reports.items():
        print(f"{mode}: {_verdict(report)}, saved to {out / f'report_{mode}.json'}")
        result = generate_test(
            args.case_folder,
            args.detection_model,
            args.detection_variant,
            mode,
            args.test_generator,
            args.cli_model,
        )
        print(f"{mode} test: {result.status}: {result.reason or result.test_file}")


if __name__ == "__main__":
    main()
