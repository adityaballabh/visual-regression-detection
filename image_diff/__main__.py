import argparse
from pathlib import Path

import cv2
import numpy as np

from image_diff.dom.parse import load_snapshot
from image_diff.output import write
from image_diff.pipeline import diff_images, pad_to_match


def _read(path: Path) -> np.ndarray:
    image = cv2.imread(str(path), cv2.IMREAD_COLOR)
    if image is None:
        raise SystemExit(f"could not read image: {path}")
    return image


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

    snapshots = None
    if args.before_snapshot is not None:
        snapshots = load_snapshot(args.before_snapshot), load_snapshot(args.after_snapshot)

    before, after = pad_to_match(_read(args.before), _read(args.after))
    changes = diff_images(before, after, snapshots)
    write(args.out, before, after, changes)

    print(f"{len(changes)} changes written to {args.out}")


if __name__ == "__main__":
    main()
