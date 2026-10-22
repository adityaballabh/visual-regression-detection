import argparse
from pathlib import Path

from image_diff.diff import diff_files


def main():
    parser = argparse.ArgumentParser(prog="image_diff")
    parser.add_argument("before", type=Path)
    parser.add_argument("after", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--before-snapshot", type=Path)
    parser.add_argument("--after-snapshot", type=Path)
    args = parser.parse_args()
    if (args.before_snapshot is None) != (args.after_snapshot is None):
        parser.error("--before-snapshot and --after-snapshot must be given together")

    snapshot_paths = None
    if args.before_snapshot is not None:
        snapshot_paths = args.before_snapshot, args.after_snapshot

    changes = diff_files(args.before, args.after, args.out, snapshot_paths)
    print(f"{len(changes)} changes written to {args.out}")


if __name__ == "__main__":
    main()
