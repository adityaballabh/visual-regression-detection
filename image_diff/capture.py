import json
from fnmatch import fnmatchcase
from itertools import compress
from pathlib import Path

from playwright.sync_api import Page

# Skip styles that never change what is drawn
_NOT_VISUAL = [
    # Animation
    "animation-*", "transition-*", "view-transition-*", "*timeline-*", "trigger-*", "interest-*", "interpolate-size",
    # Interaction
    "scroll-behavior", "overscroll-*", "caret-*", "cursor", "pointer-events", "user-select", "touch-action",
    "interactivity", "app-region", "speak", "overflow-anchor", "-webkit-user-*", "-webkit-tap-*",
    # Names, hints and CSS variables
    "anchor-name", "anchor-scope", "container-name", "reading-*", "buffered-rendering", "--*",
    # Logical duplicates
    "*block*", "*inline*", "inset-*", "border-start-*", "border-end-*", "corner-start-*", "corner-end-*",
    # Shorthands and webkit copies
    "text-decoration", "font-variant", "contain-intrinsic-size", "-webkit-box-decoration-break", "-webkit-border-image",
    "-webkit-mask-position-*", "-webkit-line-break", "-webkit-ruby-position", "-webkit-text-combine",
    "-webkit-text-orientation", "-webkit-writing-mode",
]  # fmt: skip

# Web fonts and MathJax can change the layout after the page has loaded
_WAIT_FOR_STABLE_PAGE = "async () => { await document.fonts.ready; await window.MathJax?.startup?.promise }"

# Freeze animations so the screenshot and snapshot match
_FREEZE_ANIMATIONS = """() => {
  for (const animation of document.getAnimations()) {
    animation.effect.getComputedTiming().endTime === Infinity ? animation.cancel() : animation.finish();
  }
}"""


def _is_visual(style: str) -> bool:
    return not any(fnmatchcase(style, pattern) for pattern in _NOT_VISUAL)


def _visual_styles(page: Page) -> list[str]:
    styles = page.evaluate("Array.from(getComputedStyle(document.documentElement))")
    return [style for style in styles if _is_visual(style)]


def _store_constants_once(snapshot: dict, requested: list[str]) -> dict:
    layouts = [document["layout"] for document in snapshot["documents"]]
    element_rows = []
    for layout in layouts:
        # Skip text nodes since their rows are empty
        element_rows += [row for row in layout["styles"] if row]
    columns = list(zip(*element_rows))
    varies = [len(set(column)) > 1 for column in columns]

    same_everywhere = {}
    for style, column, style_varies in zip(requested, columns, varies):
        # -1 means Chromium left the style out
        if not style_varies and column[0] >= 0:
            same_everywhere[style] = snapshot["strings"][column[0]]

    for layout in layouts:
        layout["styles"] = [list(compress(row, varies)) for row in layout["styles"]]
    return {"styles": list(compress(requested, varies)), "same_everywhere": same_everywhere}


def capture(page: Page, out_prefix: Path):
    page.evaluate(_WAIT_FOR_STABLE_PAGE)
    page.evaluate(_FREEZE_ANIMATIONS)
    page.screenshot(path=out_prefix.with_suffix(".png"), full_page=True)

    requested = _visual_styles(page)
    # Needs a Chromium-based browser
    devtools = page.context.new_cdp_session(page)
    snapshot = devtools.send("DOMSnapshot.captureSnapshot", {"computedStyles": requested, "includePaintOrder": True})
    devtools.detach()
    style_fields = _store_constants_once(snapshot, requested)

    snapshot_file = out_prefix.with_name(f"{out_prefix.name}_snapshot.json")
    file = {"device_pixel_ratio": page.evaluate("devicePixelRatio"), **style_fields, "snapshot": snapshot}
    snapshot_file.write_text(json.dumps(file))
