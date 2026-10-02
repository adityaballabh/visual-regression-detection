import json
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from image_diff.model import Box, Change, Kind, Side

_RED = (255, 0, 0)
_WHITE = (255, 255, 255)
# The outline is drawn this far outside the box, so the line sits just outside the change
_OUTLINE_WIDTH = 3
# Bundled Inter because Pillow has no bold face and thin numbers might be hard to read
_FONT = ImageFont.truetype(str(Path(__file__).parent / "fonts" / "Inter-Bold.ttf"), size=16)
_TAG_PAD_X = 4
_TAG_PAD_Y = 2


def _draw_outline(draw: ImageDraw.ImageDraw, box: Box, image_size: tuple[int, int]) -> Box:
    width, height = image_size
    outline = Box(
        max(box.x1 - _OUTLINE_WIDTH, 0),
        max(box.y1 - _OUTLINE_WIDTH, 0),
        min(box.x2 + _OUTLINE_WIDTH, width),
        min(box.y2 + _OUTLINE_WIDTH, height),
    )
    # Pillow's far corner is the last pixel but ours is one past it
    draw.rectangle((outline.x1, outline.y1, outline.x2 - 1, outline.y2 - 1), outline=_RED, width=_OUTLINE_WIDTH)
    return outline


def _tag_placement(outline: Box, tag_width: int, tag_height: int, image_size: tuple[int, int]) -> tuple[int, int]:
    width, height = image_size
    spots = []
    # Above or below the outline, lined up with its left or right edge
    for y in (outline.y1 - tag_height, outline.y2):
        for x in (outline.x1, outline.x2 - tag_width):
            spots.append((x, y))

    # Left or right of the outline, lined up with its top or bottom edge
    for y in (outline.y1, outline.y2 - tag_height):
        for x in (outline.x1 - tag_width, outline.x2):
            spots.append((x, y))

    # First spot outside the outline that fits in the image
    for x, y in spots:
        if x >= 0 and y >= 0 and x + tag_width < width and y + tag_height < height:
            return x, y

    # Place the tag inside the outline at its bottom right corner as a fallback
    return max(outline.x2 - tag_width, 0), max(outline.y2 - tag_height, 0)


def _draw_tag(draw: ImageDraw.ImageDraw, outline: Box, number: int, image_size: tuple[int, int]):
    text = str(number)
    left, top, right, bottom = draw.textbbox((0, 0), text, font=_FONT)
    tag_width = right - left + 2 * _TAG_PAD_X
    tag_height = bottom - top + 2 * _TAG_PAD_Y
    x, y = _tag_placement(outline, tag_width, tag_height, image_size)

    draw.rectangle((x, y, x + tag_width, y + tag_height), fill=_RED)
    # Center the number on the tag
    draw.text((x + tag_width / 2, y + tag_height / 2), text, font=_FONT, fill=_WHITE, anchor="mm")


def _annotate(image: np.ndarray, numbered: list[tuple[int, Change]], side: Side) -> np.ndarray:
    canvas = Image.fromarray(cv2.cvtColor(image, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(canvas)
    for number, change in numbered:
        box = change.before if side == Side.BEFORE else change.after
        if box:
            outline = _draw_outline(draw, box, canvas.size)
            _draw_tag(draw, outline, number, canvas.size)
    return cv2.cvtColor(np.asarray(canvas), cv2.COLOR_RGB2BGR)


def _box_json(box: Box | None) -> dict[str, int] | None:
    if box is None:
        return None
    return {"x": box.x1, "y": box.y1, "width": box.x2 - box.x1, "height": box.y2 - box.y1}


def write(out: Path, before: np.ndarray, after: np.ndarray, changes: tuple[Change, ...]):
    out.mkdir(parents=True, exist_ok=True)
    numbered = list(enumerate(changes, start=1))

    rows = []
    for number, change in numbered:
        row = {"id": number, "type": change.kind, "before": _box_json(change.before), "after": _box_json(change.after)}
        rows.append(f"  {json.dumps(row)}")

    # One change per line for readability
    body = ",\n".join(rows)
    boxes_json = f"[\n{body}\n]\n"
    (out / "boxes.json").write_text(boxes_json)

    # One pair of images per kind to avoid crowding
    for kind in Kind:
        kind_changes = [(number, change) for number, change in numbered if change.kind == kind]
        cv2.imwrite(str(out / f"before_{kind}.png"), _annotate(before, kind_changes, Side.BEFORE))
        cv2.imwrite(str(out / f"after_{kind}.png"), _annotate(after, kind_changes, Side.AFTER))
