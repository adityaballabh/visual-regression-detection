from pathlib import Path

import cv2

from image_diff.dom.parse import load_snapshot
from image_diff.output import write
from image_diff.pipeline import diff_images, pad_to_match

_EXAMPLES = Path(__file__).parent


def main():
    for inputs in sorted(_EXAMPLES.glob("*/input")):
        folder = inputs.parent
        before, after = pad_to_match(cv2.imread(str(inputs / "before.png")), cv2.imread(str(inputs / "after.png")))
        snapshots = load_snapshot(inputs / "before_snapshot.json"), load_snapshot(inputs / "after_snapshot.json")

        pixel = diff_images(before, after)
        dom = diff_images(before, after, snapshots)

        write(folder / "pixel", before, after, pixel)
        write(folder / "dom", before, after, dom)
        print(f"{folder.name}: {len(pixel)} pixel boxes, {len(dom)} rows")


if __name__ == "__main__":
    main()
