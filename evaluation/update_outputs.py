import argparse
from pathlib import Path

from pipeline import run_pipeline
from regression_detection.gemini_processor import DEFAULT_MODEL, VARIANTS

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def main():
    parser = argparse.ArgumentParser(prog="update_outputs")
    parser.add_argument("--detection-model", default=DEFAULT_MODEL)
    parser.add_argument("--detection-variant", choices=VARIANTS, default="all")
    parser.add_argument("--detection-dry-run", action="store_true")
    args = parser.parse_args()

    for case_folder in sorted(_EXAMPLES.glob("*/*/")):
        reports = run_pipeline(
            case_folder,
            detection_input="dom",
            detection_variant=args.detection_variant,
            detection_model=args.detection_model,
            detection_mode="both",
            detection_dry_run=args.detection_dry_run,
        )
        print(f"{case_folder.relative_to(_EXAMPLES)}: {len(reports)} reports")


if __name__ == "__main__":
    main()
