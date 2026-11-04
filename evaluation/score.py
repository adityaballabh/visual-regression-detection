import json
from pathlib import Path

import numpy as np
from sklearn.metrics import precision_score, recall_score

from pipeline import diff_folder
from regression_detection.gemini_processor import RegressionReport

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_MODES = ("context", "baseline")


def _runs() -> list[str]:
    runs = set()
    for label_file in _EXAMPLES.glob("*/*/label.json"):
        for run_folder in (label_file.parent / "out" / "regression_detection").glob("*/*"):
            runs.add(f"{run_folder.parent.name}/{run_folder.name}")
    return sorted(runs)


def _read_report(case_folder: Path, run: str, mode: str) -> RegressionReport | None:
    report_file = case_folder / "out" / "regression_detection" / run / f"report_{mode}.json"
    if not report_file.exists():
        return None
    return RegressionReport.model_validate_json(report_file.read_text())


def _read_box_ids(case_folder: Path, variant: str) -> list[int]:
    boxes = json.loads((diff_folder(case_folder, variant) / "boxes.json").read_text())
    return [box["id"] for box in boxes]


def _print_scores(name: str, truth: list[bool], predicted: list[bool]):
    if not truth:
        print(f"  {name}: no labels")
        return
    precision = precision_score(truth, predicted, zero_division=np.nan)
    recall = recall_score(truth, predicted, zero_division=np.nan)
    print(f"  {name}: precision {precision:.3f} recall {recall:.3f}")


def score(run: str, mode: str):
    case_truth = []
    case_predicted = []
    box_truth = []
    box_predicted = []
    variant = Path(run).name
    for label_file in sorted(_EXAMPLES.glob("*/*/label.json")):
        case_folder = label_file.parent
        boxes_key = f"{diff_folder(case_folder, variant).name}_boxes"
        report = _read_report(case_folder, run, mode)
        if report is None:
            print(f"skipping {case_folder.relative_to(_EXAMPLES)}: no {run} {mode} report")
            continue
        label = json.loads(label_file.read_text())
        case_truth.append(label["regression"])
        case_predicted.append(report.is_regression)
        if boxes_key in label:
            flagged_ids = {regression.box_id for regression in report.regressions}
            for box_id in _read_box_ids(case_folder, variant):
                box_truth.append(box_id in label[boxes_key])
                box_predicted.append(box_id in flagged_ids)
    print(f"{run} {mode}")
    _print_scores("cases", case_truth, case_predicted)
    _print_scores("boxes", box_truth, box_predicted)


def main():
    for run in _runs():
        for mode in _MODES:
            score(run, mode)


if __name__ == "__main__":
    main()
