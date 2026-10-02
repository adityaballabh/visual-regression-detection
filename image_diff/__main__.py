import argparse
from pathlib import Path

import cv2
import numpy as np

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
    args = parser.parse_args()

    before, after = pad_to_match(_read(args.before), _read(args.after))
    boxes = diff_images(before, after)
    write(args.out, before, after, boxes)

    print(f"{len(boxes)} changes written to {args.out}")


if __name__ == "__main__":
    main()
