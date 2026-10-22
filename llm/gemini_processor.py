"""Regression classification with Gemini.

Takes the output of the image-diff stage (four annotated screenshots plus
boxes.json), the design intent and the design language, asks Gemini whether the
change is a regression, and returns a structured report naming the offending
boxes. A no-context baseline prompt (images and boxes.json only) runs through
the same schema so the two can be compared.

Case directory layout (a case is one before/after pair):
    boxes.json            from image_diff (DOM fields optional)
    before_color.png      annotated images from image_diff
    after_color.png
    before_shape.png
    after_shape.png
    design_intent.md      what the change is supposed to do (from the PR description)
    design_language.md    themes, palettes, size restrictions, guidelines
    label.json            only for `eval`: {"regression": true, "boxes": [3, 5]}

Usage:
    python llm/gemini_processor.py run  CASE_DIR [--mode context|baseline|both] [--out DIR]
    python llm/gemini_processor.py eval CASES_DIR [--out DIR]
    add --dry-run to print the prompt without calling the API

GEMINI_API_KEY is read from the environment or from a .env file at the repo root.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemini-3.8-flash"
IMAGE_NAMES = ["before_color", "after_color", "before_shape", "after_shape"]


# ---------------------------------------------------------------- report schema


class Regression(BaseModel):
    box_id: int = Field(description="id of the numbered box in boxes.json")
    category: Literal["layout", "color", "typography", "spacing", "missing_element", "overflow", "other"]
    severity: Literal["low", "medium", "high"]
    explanation: str = Field(description="What is wrong in this box and why it is not an intended change")
    violated_rule: str | None = Field(
        default=None, description="The design intent or design language rule it breaks, if context was given"
    )


class RegressionReport(BaseModel):
    is_regression: bool
    confidence: float = Field(description="0 to 1")
    summary: str = Field(description="One or two sentences on the overall verdict")
    regressions: list[Regression] = Field(description="Empty when is_regression is false")
    intended_box_ids: list[int] = Field(description="Boxes that look like intended changes")


# ---------------------------------------------------------------------- prompts

SHARED_IMAGE_GUIDE = """\
You are given screenshots of a web page before and after a code change. Each
change found by an image diff is outlined in red and numbered; the same number
marks the same change in every image. Images are provided in this order:
  1. before_color  / 2. after_color  - color changes are outlined here
  3. before_shape  / 4. after_shape  - shape changes (resized, moved, added,
     removed elements) are outlined here. An added element only has a box on
     the "after" image, a removed one only on "before".
A change of type color_and_shape appears on all four images."""

CONTEXT_PROMPT = """\
{image_guide}

Decide whether the change introduces a visual REGRESSION: an unintended
visual defect. Changes that match the design intent are NOT regressions, even if
large. Changes that contradict the design intent or break the design language
are regressions, as are defects such as overlap, clipping, misalignment,
broken spacing, unreadable text or unexpected missing elements.

## Design intent
{design_intent}

## Design language
{design_language}

## Detected changes (boxes.json)
Coordinates are pixels in the screenshot. "detail", when present, describes the
DOM property change behind the box.
{boxes}

Report only boxes whose ids appear above. Put every box you judge to be an
intended change in intended_box_ids. If nothing is a regression set
is_regression to false and leave regressions empty."""

BASELINE_PROMPT = """\
{image_guide}

Decide whether the change introduces a visual regression (an unintended visual
defect). You have no information about what the change was meant to do.

## Detected changes (boxes.json)
{boxes}

Report only boxes whose ids appear above. If nothing is a regression set
is_regression to false and leave regressions empty."""


# ---------------------------------------------------------------------- loading


def load_env():
    """Minimal .env loader so python-dotenv isn't required."""
    env_file = REPO_ROOT / ".env"
    if not env_file.exists():
        return
    for line in env_file.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip("'\""))


class Case:
    def __init__(self, directory: Path, design_folder: Path | None = None, files: str = "all"):
        design_folder = design_folder or directory
        self.dir = directory
        self.name = directory.name
        # Which inputs go to Gemini: "all", "images" or "boxes"
        self.files = files
        boxes_file = directory / "boxes.json"
        if not boxes_file.exists():
            raise SystemExit(f"{boxes_file} not found")
        self.boxes = json.loads(boxes_file.read_text())
        self.box_ids = {b["id"] for b in self.boxes}
        self.image_paths = [directory / f"{n}.png" for n in IMAGE_NAMES]
        missing = [p for p in self.image_paths if not p.exists()]
        if missing:
            raise SystemExit(f"missing annotated images: {', '.join(map(str, missing))}")
        self.design_intent = _read_optional(design_folder / "design_intent.md", "(not provided)")
        self.design_language = _read_optional(design_folder / "design_language.md", "(not provided)")

    def boxes_for_prompt(self) -> str:
        # selector/frames are for generating assertions later, not for classification.
        slim = [{k: v for k, v in b.items() if k not in ("selector", "frames") and v is not None} for b in self.boxes]
        return json.dumps(slim, indent=1)

    def label(self) -> dict | None:
        f = self.dir / "label.json"
        return json.loads(f.read_text()) if f.exists() else None


def _read_optional(path: Path, default: str) -> str:
    return path.read_text().strip() if path.exists() else default


def build_prompt(case: Case, mode: str) -> str:
    template = CONTEXT_PROMPT if mode == "context" else BASELINE_PROMPT
    return template.format(
        image_guide=SHARED_IMAGE_GUIDE,
        design_intent=case.design_intent,
        design_language=case.design_language,
        boxes=case.boxes_for_prompt(),
    )


# ----------------------------------------------------------------------- Gemini


def classify(case: Case, mode: str, model: str, dry_run: bool = False) -> RegressionReport | None:
    prompt = build_prompt(case, mode)
    if dry_run:
        print(f"===== {case.name} [{mode}] =====\n{prompt}\n(images: {[p.name for p in case.image_paths]})\n")
        return None

    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set (put it in .env)")
    client = genai.Client(api_key=api_key)

    parts: list = [prompt]
    for name, path in zip(IMAGE_NAMES, case.image_paths):
        parts.append(f"{name}:")
        parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png"))

    response = client.models.generate_content(
        model=model,
        contents=parts,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=RegressionReport,
            temperature=0,
        ),
    )
    report = RegressionReport.model_validate_json(response.text)
    return _drop_unknown_boxes(report, case.box_ids)


def _drop_unknown_boxes(report: RegressionReport, valid_ids: set[int]) -> RegressionReport:
    """Guard against hallucinated box ids."""
    report.regressions = [r for r in report.regressions if r.box_id in valid_ids]
    report.intended_box_ids = [i for i in report.intended_box_ids if i in valid_ids]
    if not report.regressions:
        report.is_regression = False
    return report


def run_case(case: Case, mode: str, model: str, out: Path | None, dry_run: bool) -> dict[str, RegressionReport]:
    modes = ["context", "baseline"] if mode == "both" else [mode]
    reports = {}
    for m in modes:
        report = classify(case, m, model, dry_run)
        if report is None:
            continue
        reports[m] = report
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / f"report_{m}.json").write_text(report.model_dump_json(indent=2))
    return reports


# -------------------------------------------------------------------- evaluation


def _prf(tp: int, fp: int, fn: int) -> tuple[float, float]:
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    return precision, recall


def evaluate(cases_dir: Path, model: str, out: Path | None, dry_run: bool):
    """Classification (case level) and localization (box level) precision/recall."""
    cases = [Case(d) for d in sorted(cases_dir.iterdir()) if (d / "boxes.json").exists()]
    if not cases:
        raise SystemExit(f"no cases found in {cases_dir}")

    counts = {
        m: {"ctp": 0, "cfp": 0, "cfn": 0, "ctn": 0, "btp": 0, "bfp": 0, "bfn": 0} for m in ("context", "baseline")
    }
    for case in cases:
        label = case.label()
        if label is None:
            print(f"skipping {case.name}: no label.json", file=sys.stderr)
            continue
        reports = run_case(case, "both", model, out / case.name if out else None, dry_run)
        for m, report in reports.items():
            c = counts[m]
            truth, pred = label["regression"], report.is_regression
            c["ctp"] += truth and pred
            c["cfp"] += (not truth) and pred
            c["cfn"] += truth and not pred
            c["ctn"] += (not truth) and not pred
            true_boxes, pred_boxes = set(label.get("boxes", [])), {r.box_id for r in report.regressions}
            c["btp"] += len(true_boxes & pred_boxes)
            c["bfp"] += len(pred_boxes - true_boxes)
            c["bfn"] += len(true_boxes - pred_boxes)

    if dry_run:
        return
    summary = {}
    for m, c in counts.items():
        cp, cr = _prf(c["ctp"], c["cfp"], c["cfn"])
        bp, br = _prf(c["btp"], c["bfp"], c["bfn"])
        summary[m] = {
            "classification_precision": round(cp, 3),
            "classification_recall": round(cr, 3),
            "localization_precision": round(bp, 3),
            "localization_recall": round(br, 3),
            "counts": c,
        }
    print(json.dumps(summary, indent=2))
    if out:
        out.mkdir(parents=True, exist_ok=True)
        (out / "eval_summary.json").write_text(json.dumps(summary, indent=2))


# --------------------------------------------------------------------------- CLI


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="classify one case")
    run_p.add_argument("case_dir", type=Path)
    run_p.add_argument("--mode", choices=["context", "baseline", "both"], default="context")
    eval_p = sub.add_parser("eval", help="score context vs baseline over labeled cases")
    eval_p.add_argument("cases_dir", type=Path)
    for p in (run_p, eval_p):
        p.add_argument("--out", type=Path, help="write report JSON files here")
        p.add_argument("--model", default=DEFAULT_MODEL)
        p.add_argument("--dry-run", action="store_true", help="print prompts, no API call")
    args = parser.parse_args()

    load_env()
    if args.command == "run":
        reports = run_case(Case(args.case_dir), args.mode, args.model, args.out, args.dry_run)
        for m, report in reports.items():
            print(f"--- {m} ---\n{report.model_dump_json(indent=2)}")
    else:
        evaluate(args.cases_dir, args.model, args.out, args.dry_run)


if __name__ == "__main__":
    main()
