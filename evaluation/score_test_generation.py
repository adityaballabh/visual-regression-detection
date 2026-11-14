import csv
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from evaluation.score import format_cell
from pipeline import diff_folder
from test_generation.llm.generate import GenerationResult, names_box_element

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_RESULTS = Path(__file__).parent / "results" / "test_generation"
_VARIANTS = ("all", "images", "boxes", "no_snapshots")
_MODES = ("context", "baseline")
_COLUMNS = ["detection_model", "variant", "mode", "regression_count", "valid_rate", "relevant_rate", "avg_cost_usd"]

Condition = tuple[str, str, str]


def _read_results() -> dict[str, dict[Condition, list[GenerationResult]]]:
    results = defaultdict(lambda: defaultdict(list))
    for result_file in sorted(_EXAMPLES.glob("*/*/out/test_generation/**/result.json")):
        # The generator folder sits right above the detection model folder
        generator = result_file.parents[3].name
        result = GenerationResult.model_validate_json(result_file.read_text())
        condition = (result.detection_model, result.detection_variant, result.detection_mode)
        results[generator][condition].append(result)
    return results


def _true_boxes(case_folder: Path) -> list[dict]:
    label = json.loads((case_folder / "label.json").read_text())
    # Use DOM boxes for every variant since pixel boxes have no selector to look for in the output
    boxes = json.loads((diff_folder(case_folder, "all") / "boxes.json").read_text())
    return [box for box in boxes if box["id"] in label["dom_boxes"]]


def _is_relevant(result: GenerationResult) -> bool:
    true_boxes = _true_boxes(_EXAMPLES.parent / result.case)
    # A relevant test fails on the after snapshot because of a labeled regression
    return bool(names_box_element(result.attempts[-1].validation.after_output, true_boxes))


def summarize(condition: Condition, results: list[GenerationResult]) -> dict[str, str | int | float]:
    # Skipped reports found no regression, so there was no test to write
    regressions = [result for result in results if result.status != "skipped"]
    valid_tests = [result for result in regressions if result.status == "generated"]
    relevant_tests = sum(_is_relevant(result) for result in valid_tests)
    # Scripted results have no usage, so their cost reads as 0
    costs = [result.usage.total_cost_usd for result in regressions]
    detection_model, variant, mode = condition
    return {
        "detection_model": detection_model,
        "variant": variant,
        "mode": mode,
        "regression_count": len(regressions),
        "valid_rate": len(valid_tests) / len(regressions) if regressions else np.nan,
        "relevant_rate": relevant_tests / len(regressions) if regressions else np.nan,
        "avg_cost_usd": np.mean(costs) if regressions else np.nan,
    }


def _write_summary(generator: str, rows: list[dict[str, str | int | float]]):
    summary_file = _RESULTS / f"{generator}.csv"
    summary_file.parent.mkdir(parents=True, exist_ok=True)
    with summary_file.open("w", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: format_cell(value) for key, value in row.items()})
    print(f"wrote {summary_file.relative_to(_EXAMPLES.parent)}")


def main():
    for generator, results_by_condition in _read_results().items():
        rows = []
        for detection_model in sorted({model for model, _, _ in results_by_condition}):
            for variant in _VARIANTS:
                for mode in _MODES:
                    condition = (detection_model, variant, mode)
                    # The scripted generator has no no_snapshots results
                    if condition in results_by_condition:
                        rows.append(summarize(condition, results_by_condition[condition]))
        _write_summary(generator, rows)


if __name__ == "__main__":
    main()
