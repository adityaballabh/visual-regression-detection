import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
from sklearn.metrics import precision_score, recall_score

from pipeline import diff_folder
from regression_detection.gemini_processor import ReportWithUsage

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_RESULTS = Path(__file__).parent / "results" / "regression_detection"
_MODES = ("context", "baseline")
# Prices as of Nov 2026
_PRICES_PER_MTOK = {
    "gemini-3.5-flash-lite": {"input": 0.30, "output": 2.50},
    "gemini-3.6-flash": {"input": 0.75, "output": 3.75},
    "gemini-4-hydrogen": {"input": 1.50, "output": 7.50},
}
_COLUMNS = [
    "variant",
    "mode",
    "case_precision",
    "case_recall",
    "box_precision",
    "box_recall",
    "avg_input_tokens",
    "avg_output_tokens",
    "avg_cost_usd",
]


def _runs() -> list[str]:
    runs = set()
    for label_file in _EXAMPLES.glob("*/*/label.json"):
        for run_folder in (label_file.parent / "out" / "regression_detection").glob("*/*"):
            runs.add(f"{run_folder.parent.name}/{run_folder.name}")
    return sorted(runs)


def _read_report(case_folder: Path, run: str, mode: str) -> ReportWithUsage | None:
    report_file = case_folder / "out" / "regression_detection" / run / f"report_{mode}.json"
    if not report_file.exists():
        return None
    return ReportWithUsage.model_validate_json(report_file.read_text())


def _read_box_ids(case_folder: Path, variant: str) -> list[int]:
    boxes = json.loads((diff_folder(case_folder, variant) / "boxes.json").read_text())
    return [box["id"] for box in boxes]


def _precision_recall(truth: list[bool], predicted: list[bool]) -> tuple[float, float]:
    if not truth:
        return np.nan, np.nan
    precision = precision_score(truth, predicted, zero_division=np.nan)
    recall = recall_score(truth, predicted, zero_division=np.nan)
    return precision, recall


def _cost_usd(model: str, input_tokens: float, output_tokens: float) -> float:
    prices = _PRICES_PER_MTOK[model]
    return (input_tokens * prices["input"] + output_tokens * prices["output"]) / 1_000_000


def summarize(run: str, mode: str) -> dict[str, str | float]:
    case_truth = []
    case_predicted = []
    box_truth = []
    box_predicted = []
    input_tokens = []
    output_tokens = []
    variant = Path(run).name
    for label_file in sorted(_EXAMPLES.glob("*/*/label.json")):
        case_folder = label_file.parent
        boxes_key = f"{diff_folder(case_folder, variant).name}_boxes"
        report = _read_report(case_folder, run, mode)
        if report is None:
            print(f"skipping {case_folder.relative_to(_EXAMPLES)}: no {run} {mode} report")
            continue
        input_tokens.append(report.usage.text_tokens + report.usage.image_tokens)
        # Thinking is billed at the output price
        output_tokens.append(report.usage.output_tokens + report.usage.thinking_tokens)
        label = json.loads(label_file.read_text())
        case_truth.append(label["regression"])
        case_predicted.append(report.is_regression)
        if boxes_key in label:
            flagged_ids = {regression.box_id for regression in report.regressions}
            for box_id in _read_box_ids(case_folder, variant):
                box_truth.append(box_id in label[boxes_key])
                box_predicted.append(box_id in flagged_ids)
    case_precision, case_recall = _precision_recall(case_truth, case_predicted)
    box_precision, box_recall = _precision_recall(box_truth, box_predicted)
    avg_input_tokens = np.mean(input_tokens)
    avg_output_tokens = np.mean(output_tokens)
    avg_cost = _cost_usd(Path(run).parent.name, avg_input_tokens, avg_output_tokens)
    return {
        "variant": variant,
        "mode": mode,
        "case_precision": case_precision,
        "case_recall": case_recall,
        "box_precision": box_precision,
        "box_recall": box_recall,
        "avg_input_tokens": round(avg_input_tokens),
        "avg_output_tokens": round(avg_output_tokens),
        # Use 5 decimals since most calls cost under a cent
        "avg_cost_usd": f"{avg_cost:.5f}",
    }


def _write_summary(model: str, rows: list[dict[str, str | float]]):
    summary_file = _RESULTS / f"{model}.csv"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _cell(value) for key, value in row.items()})
    print(f"wrote {summary_file.relative_to(_EXAMPLES.parent)}")


def _cell(value: str | float) -> str:
    if isinstance(value, (str, int)):
        return str(value)
    return "NaN" if np.isnan(value) else f"{value:.3f}"


def main():
    rows_by_model = defaultdict(list)
    for run in _runs():
        model = Path(run).parent.name
        for mode in _MODES:
            rows_by_model[model].append(summarize(run, mode))
    for model, rows in rows_by_model.items():
        _write_summary(model, rows)


if __name__ == "__main__":
    main()
