import csv
from collections import defaultdict
from pathlib import Path

import numpy as np

from evaluation.score import format_cell
from test_generation.llm.generate import GenerationResult

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
_RESULTS = Path(__file__).parent / "results" / "test_generation"
_VARIANTS = ("all", "images", "boxes", "no_snapshots")
_MODES = ("context", "baseline")
_COLUMNS = ["detection_model", "variant", "mode", "regressions", "valid_tests", "valid_rate", "avg_cost_usd"]

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


def summarize(condition: Condition, results: list[GenerationResult]) -> dict[str, str | int | float]:
    # Skipped reports found no regression, so there was no test to write
    regressions = [result for result in results if result.status != "skipped"]
    valid_tests = sum(result.status == "generated" for result in regressions)
    # Scripted results have no usage, so their cost reads as 0
    costs = [result.usage.total_cost_usd for result in regressions]
    detection_model, variant, mode = condition
    return {
        "detection_model": detection_model,
        "variant": variant,
        "mode": mode,
        "regressions": len(regressions),
        "valid_tests": valid_tests,
        "valid_rate": valid_tests / len(regressions) if regressions else np.nan,
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
