import argparse
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

from github import Github
from github.Repository import Repository

from image_diff.capture import capture_html_pair
from image_diff.diff import diff_files
from image_diff.model import Side
from llm.gemini_processor import DEFAULT_MODEL, Case, RegressionReport, load_env, run_case

_CAPTURE_NAMES = ("before.png", "before_snapshot.json", "after.png", "after_snapshot.json")
# Hardcoded to where the PrairieLearn fork stores its design language
_REPO_DESIGN_LANGUAGE_PATH = "docs/design-standards.md"


def _has_captures(folder: Path) -> bool:
    return all((folder / name).is_file() for name in _CAPTURE_NAMES)


def _has_html_pair(folder: Path) -> bool:
    return all((folder / f"{side}.html").is_file() for side in Side)


def _pr_repo(pr_url: str) -> tuple[Repository, int]:
    owner, repo, _, number = urlparse(pr_url).path.strip("/").split("/")[:4]
    return Github().get_repo(f"{owner}/{repo}"), int(number)


def _download_pr_captures(pr_url: str, captures_folder: Path):
    repo, number = _pr_repo(pr_url)
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
    repo, _ = _pr_repo(pr_url)
    content = repo.get_contents(_REPO_DESIGN_LANGUAGE_PATH).decoded_content
    design_language.parent.mkdir(parents=True, exist_ok=True)
    design_language.write_bytes(content)


def _download_design_intent(pr_url: str, design_intent: Path):
    repo, number = _pr_repo(pr_url)
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


def run_pipeline(
    case_folder: Path, llm_input: str, llm_files: str, llm_mode: str, llm_dry_run: bool
) -> dict[str, RegressionReport]:
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

    out_folder = case_folder / "out"
    _diff(captures_folder, out_folder)

    load_env()
    case = Case(out_folder / llm_input, case_folder / "design", llm_files)
    return run_case(case, llm_mode, DEFAULT_MODEL, out_folder / "llm", llm_dry_run)


def _verdict(report: RegressionReport) -> str:
    if not report.is_regression:
        return "no regression"
    box_ids = ", ".join(str(regression.box_id) for regression in report.regressions)
    return f"regression in boxes {box_ids}"


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--llm-input", choices=["dom", "pixel"], default="dom")
    parser.add_argument("--llm-files", choices=["all", "images", "boxes"], default="all")
    parser.add_argument("--llm-mode", choices=["context", "baseline", "both"], default="context")
    parser.add_argument("--llm-dry-run", action="store_true")
    args = parser.parse_args()

    reports = run_pipeline(args.case_folder, args.llm_input, args.llm_files, args.llm_mode, args.llm_dry_run)
    for mode, report in reports.items():
        report_path = args.case_folder / "out" / "llm" / f"report_{mode}.json"
        print(f"{mode}: {_verdict(report)}, saved to {report_path}")


if __name__ == "__main__":
    main()
