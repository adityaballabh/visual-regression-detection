import argparse
import urllib.request
from collections import defaultdict
from pathlib import Path, PurePosixPath
from urllib.parse import urlparse

import cv2
from github import Github

from image_diff.capture import capture_html_pair
from image_diff.dom.parse import load_snapshot
from image_diff.model import Side
from image_diff.output import write
from image_diff.pipeline import diff_images, pad_to_match
from llm.gemini_processor import DEFAULT_MODEL, Case, RegressionReport, load_env, run_case

_CAPTURE_NAMES = ("before.png", "before_snapshot.json", "after.png", "after_snapshot.json")


def _has_captures(folder: Path) -> bool:
    return all((folder / name).is_file() for name in _CAPTURE_NAMES)


def _has_html_pair(folder: Path) -> bool:
    return all((folder / f"{side}.html").is_file() for side in Side)


def _download_pr_captures(pr_url: str, captures_folder: Path):
    # TODO: download design_intent.md too once the capture script commits it with the captures
    owner, repo, _, number = urlparse(pr_url).path.strip("/").split("/")[:4]
    pull = Github().get_repo(f"{owner}/{repo}").get_pull(int(number))

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


def _diff(captures_folder: Path, out_folder: Path):
    before = cv2.imread(str(captures_folder / "before.png"))
    after = cv2.imread(str(captures_folder / "after.png"))
    before, after = pad_to_match(before, after)
    snapshots = (
        load_snapshot(captures_folder / "before_snapshot.json"),
        load_snapshot(captures_folder / "after_snapshot.json"),
    )
    write(out_folder / "dom", before, after, diff_images(before, after, snapshots))
    write(out_folder / "pixel", before, after, diff_images(before, after))


def run_pipeline(case_folder: Path, llm_input: str, llm_mode: str, llm_dry_run: bool) -> dict[str, RegressionReport]:
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

    out_folder = case_folder / "out"
    _diff(captures_folder, out_folder)

    load_env()
    case = Case(out_folder / llm_input, case_folder / "design")
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
    parser.add_argument("--llm-mode", choices=["context", "baseline", "both"], default="context")
    parser.add_argument("--llm-dry-run", action="store_true")
    args = parser.parse_args()

    reports = run_pipeline(args.case_folder, args.llm_input, args.llm_mode, args.llm_dry_run)
    for mode, report in reports.items():
        report_path = args.case_folder / "out" / "llm" / f"report_{mode}.json"
        print(f"{mode}: {_verdict(report)}, saved to {report_path}")


if __name__ == "__main__":
    main()
