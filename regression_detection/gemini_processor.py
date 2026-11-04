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

Usage:
    python regression_detection/gemini_processor.py run  CASE_DIR [--mode context|baseline|both]
        [--variant all|images|boxes] [--out DIR]
    add --dry-run to print the prompt without calling the API

GEMINI_API_KEY is read from the environment or from a .env file at the repo root.
"""

import argparse
import json
import os
import time
from pathlib import Path
from typing import Literal

from compact_json import Formatter
from jinja2 import Environment, FileSystemLoader, StrictUndefined
from pydantic import BaseModel, Field

REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_MODEL = "gemini-3.5-flash-lite"
IMAGE_NAMES = ["before_color", "after_color", "before_shape", "after_shape"]
# Which inputs go to Gemini, for the ablation
VARIANTS = ["all", "images", "boxes", "no_snapshots"]


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


class TokenUsage(BaseModel):
    text_tokens: int
    image_tokens: int
    output_tokens: int
    thinking_tokens: int
    total_tokens: int


# Kept separate from RegressionReport since the usage should come directly from the API response
class ReportWithUsage(RegressionReport):
    usage: TokenUsage


# Keeps short lists like intended_box_ids on one line
REPORT_FORMATTER = Formatter(indent_spaces=2, omit_trailing_whitespace=True)


# ---------------------------------------------------------------------- prompts

# Keep each file's last newline so an included guide ends with its own line break
PROMPTS = Environment(
    loader=FileSystemLoader(Path(__file__).parent / "prompts"),
    trim_blocks=True,
    keep_trailing_newline=True,
    undefined=StrictUndefined,
)


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
    def __init__(self, directory: Path, design_folder: Path | None = None, variant: str = "all"):
        design_folder = design_folder or directory
        self.dir = directory
        self.name = directory.name
        self.variant = variant
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


def _read_optional(path: Path, default: str) -> str:
    return path.read_text().strip() if path.exists() else default


def build_prompt(case: Case, mode: str) -> str:
    prompt = PROMPTS.get_template(f"{mode}.md").render(
        variant=case.variant,
        design_intent=case.design_intent,
        design_language=case.design_language,
        boxes=case.boxes_for_prompt(),
    )
    return prompt.strip()


# ----------------------------------------------------------------------- Gemini


def classify(case: Case, mode: str, model: str, dry_run: bool = False) -> ReportWithUsage | None:
    prompt = build_prompt(case, mode)
    image_paths = [] if case.variant == "boxes" else case.image_paths
    if dry_run:
        print(f"===== {case.name} [{mode}] =====\n{prompt}\n(images: {[p.name for p in image_paths]})\n")
        return None

    from google import genai
    from google.genai import types

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise SystemExit("GEMINI_API_KEY not set (put it in .env)")
    # Retry server errors with backoff, rate limits are handled in _generate
    retry_options = types.HttpRetryOptions(initial_delay=10, http_status_codes=[408, 500, 502, 503, 504])
    # Time out a hung call so it gets retried instead of waiting forever
    http_options = types.HttpOptions(timeout=60_000, retry_options=retry_options)
    client = genai.Client(api_key=api_key, http_options=http_options)

    parts: list = [prompt]
    for name, path in zip(IMAGE_NAMES, image_paths):
        parts.append(f"{name}:")
        parts.append(types.Part.from_bytes(data=path.read_bytes(), mime_type="image/png"))

    config = types.GenerateContentConfig(
        response_mime_type="application/json",
        response_schema=RegressionReport,
        temperature=0,
    )
    response = _generate(client, model, parts, config)
    report = _drop_unknown_boxes(RegressionReport.model_validate_json(response.text), case.box_ids)
    metadata = response.usage_metadata
    prompt_counts = {detail.modality.name: detail.token_count for detail in metadata.prompt_tokens_details}
    usage = TokenUsage(
        text_tokens=prompt_counts.get("TEXT", 0),
        # A variant without images has no image entry
        image_tokens=prompt_counts.get("IMAGE", 0),
        output_tokens=metadata.candidates_token_count,
        # Gemini leaves this empty when the model does not think
        thinking_tokens=metadata.thoughts_token_count or 0,
        total_tokens=metadata.total_token_count,
    )
    return ReportWithUsage(**report.model_dump(), usage=usage)


def _generate(client, model: str, contents: list, config):
    from google.genai import errors

    while True:
        try:
            return client.models.generate_content(model=model, contents=contents, config=config)
        except errors.ClientError as error:
            if error.code != 429:
                raise
            details = error.details["error"]["details"]
            if _hit_daily_limit(details):
                raise SystemExit(f"Daily request limit reached for {model}. {error.message}") from error
            time.sleep(_retry_delay(details))


def _hit_daily_limit(details: list[dict]) -> bool:
    for detail in details:
        for violation in detail.get("violations", []):
            if "PerDay" in violation["quotaId"]:
                return True
    return False


def _retry_delay(details: list[dict]) -> float:
    for detail in details:
        if "retryDelay" in detail:
            return float(detail["retryDelay"].removesuffix("s"))
    # Wait out the per-minute window when Gemini gives no delay
    return 60


def _drop_unknown_boxes(report: RegressionReport, valid_ids: set[int]) -> RegressionReport:
    """Guard against hallucinated box ids."""
    report.regressions = [r for r in report.regressions if r.box_id in valid_ids]
    report.intended_box_ids = [i for i in report.intended_box_ids if i in valid_ids]
    if not report.regressions:
        report.is_regression = False
    return report


def run_case(case: Case, mode: str, model: str, out: Path | None, dry_run: bool) -> dict[str, ReportWithUsage]:
    modes = ["context", "baseline"] if mode == "both" else [mode]
    reports = {}
    for m in modes:
        report = classify(case, m, model, dry_run)
        if report is None:
            continue
        reports[m] = report
        if out:
            out.mkdir(parents=True, exist_ok=True)
            (out / f"report_{m}.json").write_text(REPORT_FORMATTER.serialize(report.model_dump()))
    return reports


# --------------------------------------------------------------------------- CLI


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    run_p = sub.add_parser("run", help="classify one case")
    run_p.add_argument("case_dir", type=Path)
    run_p.add_argument("--mode", choices=["context", "baseline", "both"], default="context")
    run_p.add_argument("--variant", choices=VARIANTS, default="all")
    run_p.add_argument("--out", type=Path, help="write report JSON files here")
    run_p.add_argument("--model", default=DEFAULT_MODEL)
    run_p.add_argument("--dry-run", action="store_true", help="print prompts, no API call")
    args = parser.parse_args()

    load_env()
    reports = run_case(Case(args.case_dir, variant=args.variant), args.mode, args.model, args.out, args.dry_run)
    for m, report in reports.items():
        print(f"--- {m} ---\n{report.model_dump_json(indent=2)}")


if __name__ == "__main__":
    main()
