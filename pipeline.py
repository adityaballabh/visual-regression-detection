import argparse
import shutil
from pathlib import Path

import cv2

from image_diff.capture import capture_html_pair
from image_diff.dom.parse import load_snapshot
from image_diff.model import Side
from image_diff.output import write
from image_diff.pipeline import diff_images, pad_to_match
from llm.gemini_processor import DEFAULT_MODEL, Case, load_env, run_case


def _has_captures(folder: Path) -> bool:
    for side in Side:
        for name in (f"{side}.png", f"{side}_snapshot.json"):
            if not (folder / name).is_file():
                return False
    return True


def _has_html_pair(folder: Path) -> bool:
    return all((folder / f"{side}.html").is_file() for side in Side)


def _diff(captures_folder: Path, dom_folder: Path):
    before = cv2.imread(str(captures_folder / "before.png"))
    after = cv2.imread(str(captures_folder / "after.png"))
    before, after = pad_to_match(before, after)
    snapshots = (
        load_snapshot(captures_folder / "before_snapshot.json"),
        load_snapshot(captures_folder / "after_snapshot.json"),
    )
    write(dom_folder, before, after, diff_images(before, after, snapshots))


def _copy_design_files(design_folder: Path, dom_folder: Path):
    # The LLM step reads these from the diff output folder, and runs without them if missing
    for name in ("design_intent.md", "design_language.md"):
        if (design_folder / name).is_file():
            shutil.copy(design_folder / name, dom_folder / name)


def main():
    parser = argparse.ArgumentParser(prog="pipeline")
    parser.add_argument("case_folder", type=Path)
    parser.add_argument("--llm-mode", choices=["context", "baseline", "both"], default="context")
    parser.add_argument("--llm-dry-run", action="store_true")
    args = parser.parse_args()

    captures_folder = args.case_folder / "captures"
    html_folder = args.case_folder / "html"
    # Use given captures directly from PrairieLearn or capture them from html
    if not _has_captures(captures_folder):
        if not _has_html_pair(html_folder):
            raise SystemExit(f"{args.case_folder} needs either html/ or captures/ with the screenshots and snapshots")
        capture_html_pair(html_folder, captures_folder)

    dom_folder = args.case_folder / "out" / "dom"
    _diff(captures_folder, dom_folder)
    _copy_design_files(args.case_folder / "design", dom_folder)

    load_env()
    llm_folder = args.case_folder / "out" / "llm"
    reports = run_case(Case(dom_folder), args.llm_mode, DEFAULT_MODEL, llm_folder, args.llm_dry_run)
    for mode, report in reports.items():
        print(f"--- {mode} ---\n{report.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
