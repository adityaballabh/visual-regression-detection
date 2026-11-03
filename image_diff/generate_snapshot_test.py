"""Generate a unittest that compares a captured DOM snapshot to before or after."""

import argparse
import json
from pathlib import Path

from image_diff.dom.parse import load_snapshot


def generate_test(before: Path, after: Path, side: str, output: Path, *, force: bool = False) -> Path:
    if side not in ("before", "after"):
        raise ValueError(f"Unsupported expected side: {side}")
    if not output.name.startswith("test_") or output.suffix != ".py":
        raise ValueError("Output filename must start with 'test_' and end with '.py'.")

    # Validate both inputs before writing any generated files.
    load_snapshot(before)
    load_snapshot(after)

    expected_path = output.with_name(f"{output.stem}.expected.json")
    generated_paths = {output.resolve(), expected_path.resolve()}
    if generated_paths & {before.resolve(), after.resolve()}:
        raise ValueError("Generated test and expected snapshot must not overwrite either input snapshot.")
    existing = [path for path in (output, expected_path) if path.exists()]
    if existing and not force:
        files = ", ".join(map(str, existing))
        raise FileExistsError(f"Generated output already exists: {files}. Use --force to replace it.")

    output.parent.mkdir(parents=True, exist_ok=True)
    expected_path.write_bytes((before if side == "before" else after).read_bytes())
    output.write_text(
        f'''"""Generated DOM snapshot test; expected page state: {side}."""

import os
import unittest
from pathlib import Path

from image_diff.snapshot_test import assert_snapshot_matches

EXPECTED_SNAPSHOT = Path(__file__).with_name({expected_path.name!r})


class GeneratedSnapshotTest(unittest.TestCase):
    def test_dom_matches_{side}_snapshot(self):
        actual_path = os.environ.get("ACTUAL_SNAPSHOT")
        self.assertTrue(actual_path, "Set ACTUAL_SNAPSHOT to the captured DOM snapshot to verify.")
        assert_snapshot_matches(EXPECTED_SNAPSHOT, Path(actual_path))


if __name__ == "__main__":
    unittest.main()
''',
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a unittest that checks a captured DOM snapshot against the before or after state."
    )
    parser.add_argument("before", type=Path, help="Before DOM snapshot JSON")
    parser.add_argument("after", type=Path, help="After DOM snapshot JSON")
    parser.add_argument(
        "--side",
        choices=("before", "after"),
        required=True,
        help="Snapshot state the test should pass",
    )
    parser.add_argument("--output", type=Path, required=True, help="Generated test filename (must start with test_)")
    parser.add_argument("--force", action="store_true", help="Replace generated files if they already exist")
    args = parser.parse_args()

    try:
        output = generate_test(args.before, args.after, args.side, args.output, force=args.force)
    except (OSError, ValueError, json.JSONDecodeError, SystemExit) as error:
        parser.error(str(error))
    print(f"Generated {output} and {output.with_name(f'{output.stem}.expected.json')}")


if __name__ == "__main__":
    main()
