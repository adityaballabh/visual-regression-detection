import argparse
from pathlib import Path

from pipeline import detect_regressions, prepare_case
from regression_detection.gemini_processor import DEFAULT_MODEL, VARIANTS

_EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def main():
    parser = argparse.ArgumentParser(prog="update_outputs")
    parser.add_argument("--detection-model", default=DEFAULT_MODEL)
    parser.add_argument("--detection-variant", choices=VARIANTS, help="run only this variant, every one by default")
    parser.add_argument("--detection-dry-run", action="store_true")
    args = parser.parse_args()

    variants = [args.detection_variant] if args.detection_variant else VARIANTS
    for case_folder in sorted(_EXAMPLES.glob("*/*/")):
        prepare_case(case_folder)
        for variant in variants:
            reports = detect_regressions(
                case_folder,
                detection_input="dom",
                detection_variant=variant,
                detection_model=args.detection_model,
                detection_mode="both",
                detection_dry_run=args.detection_dry_run,
            )
            print(f"{case_folder.relative_to(_EXAMPLES)} {variant}: {len(reports)} reports")


if __name__ == "__main__":
    main()
