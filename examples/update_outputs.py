import argparse
from pathlib import Path

from pipeline import run_pipeline

_EXAMPLES = Path(__file__).parent


def main():
    parser = argparse.ArgumentParser(prog="update_outputs")
    parser.add_argument("--llm-dry-run", action="store_true")
    args = parser.parse_args()

    for case_folder in sorted(_EXAMPLES.glob("*/*/")):
        reports = run_pipeline(
            case_folder, llm_input="dom", llm_files="all", llm_mode="both", llm_dry_run=args.llm_dry_run
        )
        print(f"{case_folder.relative_to(_EXAMPLES)}: {len(reports)} reports")


if __name__ == "__main__":
    main()
