import argparse
from pathlib import Path

import cv2

from image_diff.capture import capture_html_pair
from image_diff.dom.parse import load_snapshot
from image_diff.model import Side
from image_diff.output import write
from image_diff.pipeline import diff_images, pad_to_match
from llm.gemini_processor import DEFAULT_MODEL, Case, RegressionReport, load_env, run_case


def _has_captures(folder: Path) -> bool:
    for side in Side:
        for name in (f"{side}.png", f"{side}_snapshot.json"):
            if not (folder / name).is_file():
                return False
    return True


def _has_html_pair(folder: Path) -> bool:
    return all((folder / f"{side}.html").is_file() for side in Side)


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
    # Use given captures directly from PrairieLearn or capture them from html
    if not _has_captures(captures_folder):
        if not _has_html_pair(html_folder):
            raise SystemExit(f"{case_folder} needs either html/ or captures/ with the screenshots and snapshots")
        capture_html_pair(html_folder, captures_folder)

    out_folder = case_folder / "out"
    _diff(captures_folder, out_folder)

    load_env()
    case = Case(out_folder / llm_input, case_folder / "design")
    return run_case(case, llm_mode, DEFAULT_MODEL, out_folder / "llm", llm_dry_run)


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--llm-input", choices=["dom", "pixel"], default="dom")
    parser.add_argument("--llm-mode", choices=["context", "baseline", "both"], default="context")
    parser.add_argument("--llm-dry-run", action="store_true")
    args = parser.parse_args()

    reports = run_pipeline(args.case_folder, args.llm_input, args.llm_mode, args.llm_dry_run)
    for mode, report in reports.items():
        print(f"--- {mode} ---\n{report.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
